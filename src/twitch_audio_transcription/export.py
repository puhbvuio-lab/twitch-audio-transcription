"""JSON-first transcript exports derived from canonical analysis-time segments."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from .io import AudioJobPaths
from .models import TranscriptSegment


@dataclass(frozen=True)
class ExportArtifacts:
    json_path: Path
    csv_path: Path
    srt_path: Path
    vtt_path: Path


def _milliseconds(seconds: float) -> int:
    return int((Decimal(str(max(0.0, seconds))) * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _timestamp(seconds: float, separator: str) -> str:
    value = _milliseconds(seconds)
    hours, value = divmod(value, 3_600_000)
    minutes, value = divmod(value, 60_000)
    whole_seconds, milliseconds = divmod(value, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{milliseconds:03d}"


def export_transcript(segments: Iterable[TranscriptSegment], paths: AudioJobPaths) -> ExportArtifacts:
    canonical = list(segments)
    artifacts = ExportArtifacts(paths.transcript_dir / "transcript.json", paths.transcript_dir / "transcript.csv", paths.transcript_dir / "transcript.srt", paths.transcript_dir / "transcript.vtt")
    payload = {"segments": [segment.to_dict() for segment in canonical]}
    artifacts.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["start_seconds", "end_seconds", "text", "language", "average_log_probability"]
    with artifacts.csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(segment.to_dict() for segment in canonical)
    srt = "\n\n".join(f"{index}\n{_timestamp(segment.start_seconds, ',')} --> {_timestamp(segment.end_seconds, ',')}\n{segment.text}" for index, segment in enumerate(canonical, 1))
    artifacts.srt_path.write_text(srt + ("\n" if srt else ""), encoding="utf-8")
    vtt_entries = "\n\n".join(f"{_timestamp(segment.start_seconds, '.')} --> {_timestamp(segment.end_seconds, '.')}\n{segment.text}" for segment in canonical)
    artifacts.vtt_path.write_text("WEBVTT\n\n" + vtt_entries + ("\n" if vtt_entries else ""), encoding="utf-8")
    return artifacts
