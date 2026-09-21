"""Deterministic FFmpeg conversion to analysis-relative 16 kHz mono WAV."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from .config import AudioJobConfig
from .io import AudioJobPaths, atomic_write_json
from .models import AudioArtifact


def _run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-800:] or "ffmpeg failed")


def extract_audio(source: Path, config: AudioJobConfig, paths: AudioJobPaths, runner: Callable[[list[str]], None] | None = None) -> AudioArtifact:
    """Extract a WAV whose first sample always represents analysis time zero."""
    output = paths.audio_dir / "analysis.wav"
    is_vod = config.vod_url is not None
    seek = 0.0 if is_vod else float(config.start_seconds or 0)
    duration = None if config.end_seconds is None else float(config.end_seconds - (config.start_seconds or 0))
    command = ["ffmpeg", "-y", "-ss", str(seek), "-i", str(source)]
    if duration is not None:
        command.extend(["-t", str(duration)])
    command.extend(["-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(output)])
    (runner or _run_ffmpeg)(command)
    if not output.is_file():
        raise RuntimeError("ffmpeg did not create analysis.wav")
    artifact = AudioArtifact(output, 16000, 1, float(config.start_seconds or 0), duration)
    atomic_write_json(paths.audio_dir / "metadata.json", artifact.to_dict())
    return artifact
