from __future__ import annotations

import csv
import json
from pathlib import Path

from twitch_audio_transcription.config import AudioJobConfig
from twitch_audio_transcription.export import export_transcript
from twitch_audio_transcription.io import AudioJobPaths
from twitch_audio_transcription.models import TranscriptSegment


def test_export_derives_all_formats_from_one_canonical_segment(tmp_path: Path) -> None:
    media = tmp_path / "source.wav"
    media.write_bytes(b"x")
    paths = AudioJobPaths.create(AudioJobConfig(media_path=media, output_dir=tmp_path / "out"))
    segments = [TranscriptSegment(0.999, 1.0, "one second", "en", -0.1)]

    artifacts = export_transcript(segments, paths)

    payload = json.loads(artifacts.json_path.read_text(encoding="utf-8"))
    row = next(csv.DictReader(artifacts.csv_path.open(encoding="utf-8")))
    assert payload["segments"][0]["start_seconds"] == 0.999
    assert row["end_seconds"] == "1.0"
    assert "00:00:00,999 --> 00:00:01,000" in artifacts.srt_path.read_text(encoding="utf-8")
    assert "00:00:00.999 --> 00:00:01.000" in artifacts.vtt_path.read_text(encoding="utf-8")
