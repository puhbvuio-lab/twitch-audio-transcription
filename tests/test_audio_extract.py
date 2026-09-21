from __future__ import annotations

from pathlib import Path

from twitch_audio_transcription.audio_extract import extract_audio
from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.io import AudioJobPaths


class FakeRunner:
    def __init__(self) -> None:
        self.command: list[str] = []

    def __call__(self, command: list[str]) -> None:
        self.command = command
        Path(command[-1]).write_bytes(b"RIFF")


def test_extract_audio_creates_standard_wav_with_analysis_relative_timing(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"source")
    config = AudioJobConfig(
        media_path=source, start_seconds=5, end_seconds=8, output_dir=tmp_path / "out", job_id="job"
    )
    paths = AudioJobPaths.create(config)
    runner = FakeRunner()

    artifact = extract_audio(source, config, paths, runner)

    assert artifact.path == paths.audio_dir / "analysis.wav"
    assert artifact.path.exists()
    assert artifact.sample_rate == 16000
    assert artifact.channels == 1
    assert artifact.source_offset_seconds == 5
    assert artifact.duration_seconds == 3
    assert runner.command[:4] == ["ffmpeg", "-y", "-ss", "5.0"]
    assert ["-ar", "16000"] in [runner.command[i : i + 2] for i in range(len(runner.command))]
    assert ["-ac", "1"] in [runner.command[i : i + 2] for i in range(len(runner.command))]
