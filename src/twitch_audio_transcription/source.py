"""Read-only local-source handling and a replaceable yt-dlp VOD adapter."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import AudioJobConfig
from .io import AudioJobPaths, atomic_write_json


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class SourceArtifact:
    path: Path
    kind: str
    source_offset_seconds: float


class VodDownloader(Protocol):
    def download(self, vod_url: object, target_dir: Path, start_seconds: float | None, end_seconds: float | None, cookie_source: str | None) -> Path: ...


class YtDlpVodDownloader:
    """yt-dlp implementation kept behind a tiny, fakeable interface."""

    def __init__(self, executable: str = "yt-dlp", runner=None) -> None:
        self.executable = executable
        self.runner = runner or self._run

    @staticmethod
    def _run(command: list[str]) -> None:
        result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError(result.stderr[-800:] or "yt-dlp failed")

    def download(self, vod_url: object, target_dir: Path, start_seconds: float | None, end_seconds: float | None, cookie_source: str | None) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        output_template = target_dir / "vod.%(ext)s"
        command = [self.executable, "--no-playlist", "--continue", "-o", str(output_template)]
        if start_seconds is not None:
            end = "inf" if end_seconds is None else str(end_seconds)
            command.extend(["--download-sections", f"*{start_seconds}-{end}"])
        if cookie_source:
            command.extend(["--cookies-from-browser", cookie_source])
        command.append(str(vod_url))
        self.runner(command)
        candidates = sorted(path for path in target_dir.glob("vod.*") if path.suffix not in {".part", ".ytdl"})
        if not candidates:
            raise RuntimeError("yt-dlp did not create media beneath 01_source")
        return candidates[0]


def prepare_source(config: AudioJobConfig, paths: AudioJobPaths, downloader: VodDownloader | None = None) -> SourceArtifact:
    """Return one media path while recording credential-free source metadata."""
    if config.media_path is not None:
        source = config.media_path.resolve()
        stat = source.stat()
        atomic_write_json(paths.source_metadata, {"kind": "local", "path": str(source), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(source)})
        return SourceArtifact(source, "local", float(config.start_seconds or 0))
    if downloader is None:
        downloader = YtDlpVodDownloader()
    try:
        source = downloader.download(
            config.vod_url,
            paths.source_dir,
            config.start_seconds,
            config.end_seconds,
            config.browser_cookie_source,
        )
    except Exception as error:
        # Adapters may include their command line in an error.  That command
        # can carry a browser-cookie selector, so preserve the useful stage
        # context without propagating credential-bearing adapter text.
        raise RuntimeError("VOD download failed; inspect the downloader locally") from error
    source = source.resolve()
    if not source.is_relative_to(paths.source_dir.resolve()):
        raise ValueError("VOD downloader returned a path outside 01_source")
    stat = source.stat()
    atomic_write_json(paths.source_metadata, {"kind": "vod", "vod_url": str(config.vod_url), "path": str(source), "size": stat.st_size, "sha256": sha256_file(source), "start_seconds": config.start_seconds, "end_seconds": config.end_seconds})
    return SourceArtifact(source, "vod", float(config.start_seconds or 0))
