from __future__ import annotations

from pathlib import Path

from twitch_audio_transcription.audio_extract import extract_audio
from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.device import DeviceSelection
from twitch_audio_transcription.export import export_transcript
from twitch_audio_transcription.io import AudioJobPaths
from twitch_audio_transcription.transcription import transcribe


class Runner:
    def __call__(self, command: list[str]) -> None:
        Path(command[-1]).write_bytes(b"RIFF fixture")


class Engine:
    def transcribe(self, *_args):
        return ([{"start": 0, "end": 0.5, "text": "fixture"}], {"language": "en"})


def test_offline_local_fixture_runs_extract_transcribe_export(tmp_path: Path) -> None:
    fixture = tmp_path / "tone.wav"
    fixture.write_bytes(b"tiny wave fixture")
    config = AudioJobConfig(media_path=fixture, output_dir=tmp_path / "out", transcription_device="cpu")
    paths = AudioJobPaths.create(config)
    audio = extract_audio(fixture, config, paths, Runner())
    segments = transcribe(audio, config, Engine())
    exported = export_transcript(segments, paths)
    assert exported.vtt_path.exists()
