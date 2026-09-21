from __future__ import annotations

from pathlib import Path

from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.io import AudioJobPaths
from twitch_audio_transcription.state import JobState


def config_for(tmp_path: Path) -> AudioJobConfig:
    media = tmp_path / "input.wav"
    media.write_bytes(b"audio")
    return AudioJobConfig(media_path=media, output_dir=tmp_path / "out", job_id="example")


def test_paths_create_project_layout_and_state_skips_only_matching_complete_artifacts(tmp_path: Path) -> None:
    paths = AudioJobPaths.create(config_for(tmp_path))
    assert paths.source_dir.is_dir()
    assert paths.audio_dir.is_dir()
    assert paths.transcript_dir.is_dir()
    state = JobState(paths)
    artifact = paths.source_dir / "metadata.json"
    artifact.write_text("{}", encoding="utf-8")
    fingerprint = {"source": "one"}

    assert state.should_run("acquire", fingerprint, [artifact])
    state.start("acquire", fingerprint)
    state.complete("acquire", fingerprint, [artifact])

    assert not state.should_run("acquire", fingerprint, [artifact])
    assert state.should_run("acquire", {"source": "changed"}, [artifact])
    assert state.should_run("acquire", fingerprint, [paths.source_dir / "gone.json"])


def test_fail_writes_a_terminal_redacted_state_atomically(tmp_path: Path) -> None:
    paths = AudioJobPaths.create(config_for(tmp_path))
    state = JobState(paths)
    state.start("audio", {"input": "hash"})
    state.fail("audio", {"input": "hash"}, RuntimeError("ffmpeg unavailable"))

    record = state.read("audio")
    assert record["status"] == "failed"
    assert record["error"] == "ffmpeg unavailable"
    assert not paths.stage_state("audio").with_suffix(".json.tmp").exists()
