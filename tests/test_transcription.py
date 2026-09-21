from __future__ import annotations

from pathlib import Path

from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.device import DeviceSelection
from twitch_audio_transcription.models import AudioArtifact
from twitch_audio_transcription.transcription import transcribe, transcribe_with_metadata


class FakeEngine:
    def __init__(self, fail_cuda: bool = False) -> None:
        self.fail_cuda = fail_cuda
        self.selections: list[str] = []

    def transcribe(self, audio_path: Path, selection: DeviceSelection, config: AudioJobConfig):
        self.selections.append(selection.device)
        if self.fail_cuda and selection.device == "cuda":
            raise RuntimeError("CUDA runtime failed")
        return ([{"start": 0.25, "end": 1.5, "text": " hello ", "avg_logprob": -0.2}], {"language": "en"})


def config_for(tmp_path: Path, device: str = "cpu") -> AudioJobConfig:
    media = tmp_path / "source.wav"
    media.write_bytes(b"x")
    return AudioJobConfig(media_path=media, transcription_device=device, output_dir=tmp_path / "out")


def test_transcribe_converts_engine_values_to_canonical_segments(tmp_path: Path) -> None:
    audio = AudioArtifact(tmp_path / "analysis.wav", 16000, 1, 0, 2)
    result = transcribe(audio, config_for(tmp_path), FakeEngine())
    assert result[0].text == "hello"
    assert result[0].start_seconds == 0.25
    assert result[0].language == "en"


def test_auto_runtime_cuda_failure_retries_cpu_and_records_reason(tmp_path: Path) -> None:
    audio = AudioArtifact(tmp_path / "analysis.wav", 16000, 1, 0, 2)
    engine = FakeEngine(fail_cuda=True)
    result = transcribe_with_metadata(audio, config_for(tmp_path, "auto"), engine, probe=lambda: (True, None))
    assert engine.selections == ["cuda", "cpu"]
    assert result.selection.device == "cpu"
    assert "CUDA runtime failed" in (result.selection.fallback_reason or "")
