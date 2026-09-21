from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from twitch_audio_transcription.config import AudioJobConfig


def write_job(tmp_path: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "media_path": str(tmp_path / "recording.mp4"),
        "transcription_device": "auto",
    }
    payload.update(overrides)
    path = tmp_path / "job.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_from_file_rejects_when_no_source_is_configured(tmp_path: Path) -> None:
    job = write_job(tmp_path, media_path=None)

    with pytest.raises(ValidationError, match="exactly one"):
        AudioJobConfig.from_file(job)


def test_from_file_rejects_both_sources_before_checking_local_path(tmp_path: Path) -> None:
    job = write_job(tmp_path, vod_url="https://www.twitch.tv/videos/123")

    with pytest.raises(ValidationError, match="exactly one"):
        AudioJobConfig.from_file(job)


def test_from_file_rejects_missing_local_media_path(tmp_path: Path) -> None:
    job = write_job(tmp_path)

    with pytest.raises(ValidationError, match="does not exist"):
        AudioJobConfig.from_file(job)


@pytest.mark.parametrize(
    ("start_seconds", "end_seconds"),
    [(10, 10), (10, 5)],
)
def test_from_file_rejects_equal_or_reversed_bounds(
    tmp_path: Path, start_seconds: int, end_seconds: int
) -> None:
    media = tmp_path / "recording.mp4"
    media.touch()
    job = write_job(
        tmp_path, start_seconds=start_seconds, end_seconds=end_seconds
    )

    with pytest.raises(ValidationError, match="greater than start_seconds"):
        AudioJobConfig.from_file(job)


@pytest.mark.parametrize("device", ["auto", "cuda", "cpu"])
def test_from_file_accepts_allowed_transcription_devices(
    tmp_path: Path, device: str
) -> None:
    media = tmp_path / "recording.mp4"
    media.touch()
    job = write_job(tmp_path, transcription_device=device)

    assert AudioJobConfig.from_file(job).transcription_device == device


def test_from_file_rejects_unknown_transcription_device(tmp_path: Path) -> None:
    media = tmp_path / "recording.mp4"
    media.touch()
    job = write_job(tmp_path, transcription_device="metal")

    with pytest.raises(ValidationError):
        AudioJobConfig.from_file(job)


def test_redacted_snapshot_excludes_runtime_cookie_source(tmp_path: Path) -> None:
    media = tmp_path / "recording.mp4"
    media.touch()
    job = write_job(tmp_path, browser_cookie_source="chrome")

    snapshot = AudioJobConfig.from_file(job).redacted_snapshot()

    assert "browser_cookie_source" not in snapshot
    assert snapshot["media_path"] == str(media)
