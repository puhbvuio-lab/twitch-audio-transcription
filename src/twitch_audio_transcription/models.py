"""Shared, canonical data objects for the audio-only workflow."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

TranscriptionDevice = Literal["auto", "cuda", "cpu"]


@dataclass(frozen=True)
class AudioArtifact:
    path: Path
    sample_rate: int
    channels: int
    source_offset_seconds: float
    duration_seconds: float | None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        return payload


@dataclass(frozen=True)
class TranscriptSegment:
    """One transcript segment on the analysis-audio time axis."""

    start_seconds: float
    end_seconds: float
    text: str
    language: str | None = None
    average_log_probability: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "language": self.language,
            "average_log_probability": self.average_log_probability,
        }
