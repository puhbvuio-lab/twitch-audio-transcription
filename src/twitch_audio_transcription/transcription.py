"""Faster-Whisper adapter that normalizes all output to TranscriptSegment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import AudioJobConfig
from .device import DeviceSelection, default_cuda_probe, select_device
from .models import AudioArtifact, TranscriptSegment


class TranscriptionEngine(Protocol):
    def transcribe(self, audio_path: Path, selection: DeviceSelection, config: AudioJobConfig) -> tuple[object, object]: ...


class FasterWhisperEngine:
    """Lazy dependency wrapper; importing this project never downloads a model."""

    def transcribe(self, audio_path: Path, selection: DeviceSelection, config: AudioJobConfig) -> tuple[object, object]:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("faster-whisper is required for real transcription") from error
        model = WhisperModel(config.model_size, device=selection.device, compute_type=config.compute_type or selection.compute_type, cpu_threads=config.cpu_threads or 0)
        return model.transcribe(str(audio_path), language=config.language, vad_filter=config.vad_filter, batch_size=config.batch_size)


@dataclass(frozen=True)
class TranscriptionResult:
    segments: list[TranscriptSegment]
    selection: DeviceSelection


def _value(value: object, key: str, default: object = None) -> object:
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _convert(raw_segments: object, info: object, config: AudioJobConfig) -> list[TranscriptSegment]:
    language = config.language or _value(info, "language")
    result: list[TranscriptSegment] = []
    for raw in raw_segments:  # generators returned by Faster-Whisper are supported
        text = str(_value(raw, "text", "")).strip()
        if not text:
            continue
        start = float(_value(raw, "start", 0.0))
        end = float(_value(raw, "end", start))
        if end < start:
            raise ValueError("transcription segment ends before it starts")
        logprob = _value(raw, "avg_logprob")
        result.append(TranscriptSegment(start, end, text, str(language) if language else None, float(logprob) if logprob is not None else None))
    return result


def transcribe_with_metadata(audio: AudioArtifact, config: AudioJobConfig, engine: TranscriptionEngine | None = None, *, probe=default_cuda_probe) -> TranscriptionResult:
    engine = engine or FasterWhisperEngine()
    selection = select_device(config.transcription_device, probe)
    try:
        raw_segments, info = engine.transcribe(audio.path, selection, config)
        return TranscriptionResult(_convert(raw_segments, info, config), selection)
    except Exception as error:
        if config.transcription_device != "auto" or selection.device != "cuda":
            raise
        fallback = DeviceSelection("cpu", "int8", f"CUDA runtime failed; using CPU: {error}")
        raw_segments, info = engine.transcribe(audio.path, fallback, config)
        return TranscriptionResult(_convert(raw_segments, info, config), fallback)


def transcribe(audio: AudioArtifact, config: AudioJobConfig, engine: TranscriptionEngine | None = None) -> list[TranscriptSegment]:
    return transcribe_with_metadata(audio, config, engine).segments
