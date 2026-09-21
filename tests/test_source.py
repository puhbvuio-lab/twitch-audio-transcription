from __future__ import annotations

import json
from pathlib import Path

import pytest
from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.io import AudioJobPaths
from twitch_audio_transcription.source import prepare_source


class FakeDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def download(self, vod_url, target_dir, start_seconds, end_seconds, cookie_source):
        self.calls.append((str(vod_url), target_dir, start_seconds, end_seconds, cookie_source))
        output = target_dir / "downloaded.mp4"
        output.write_bytes(b"downloaded")
        return output


def test_prepare_local_source_is_read_only_and_records_fingerprint(tmp_path: Path) -> None:
    media = tmp_path / "recording.mp4"
    original = b"original media bytes"
    media.write_bytes(original)
    config = AudioJobConfig(media_path=media, output_dir=tmp_path / "out", job_id="local")
    paths = AudioJobPaths.create(config)

    artifact = prepare_source(config, paths, FakeDownloader())

    assert artifact.path == media.resolve()
    assert media.read_bytes() == original
    metadata = json.loads(paths.source_metadata.read_text(encoding="utf-8"))
    assert metadata["kind"] == "local"
    assert metadata["sha256"]
    assert not list(paths.source_dir.glob("*.mp4"))


def test_prepare_vod_forwards_bounds_and_runtime_cookie_without_persisting_it(tmp_path: Path) -> None:
    config = AudioJobConfig(
        vod_url="https://www.twitch.tv/videos/12345",
        start_seconds=12,
        end_seconds=34,
        browser_cookie_source="edge:profile=secret",
        output_dir=tmp_path / "out",
        job_id="vod",
    )
    paths = AudioJobPaths.create(config)
    downloader = FakeDownloader()

    artifact = prepare_source(config, paths, downloader)

    assert artifact.path == paths.source_dir / "downloaded.mp4"
    assert downloader.calls[0][2:] == (12.0, 34.0, "edge:profile=secret")
    persisted = paths.source_metadata.read_text(encoding="utf-8")
    assert "secret" not in persisted
    assert json.loads(persisted)["kind"] == "vod"


def test_prepare_vod_does_not_propagate_a_cookie_value_in_download_errors(tmp_path: Path) -> None:
    class FailingDownloader:
        def download(self, *_args):
            raise RuntimeError("yt-dlp rejected edge:profile=secret")

    config = AudioJobConfig(
        vod_url="https://www.twitch.tv/videos/12345",
        browser_cookie_source="edge:profile=secret",
        output_dir=tmp_path / "out",
    )
    with pytest.raises(RuntimeError) as error:
        prepare_source(config, AudioJobPaths.create(config), FailingDownloader())

    assert "secret" not in str(error.value)
