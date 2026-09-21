"""Job-local paths and JSON utilities.

Everything this project writes lives below one configured job directory.  This
keeps source media read-only and makes a job portable to another machine.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import AudioJobConfig


def atomic_write_json(path: Path, payload: Any) -> None:
    """Atomically replace a JSON file, never leaving a partially-written state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    os.replace(temporary, path)


@dataclass(frozen=True)
class AudioJobPaths:
    root: Path
    source_dir: Path
    audio_dir: Path
    transcript_dir: Path
    status_dir: Path

    @classmethod
    def create(cls, config: AudioJobConfig) -> "AudioJobPaths":
        root = (config.output_dir / config.job_id).expanduser().resolve()
        paths = cls(root, root / "01_source", root / "02_audio", root / "03_transcript", root / "09_status")
        for directory in (paths.source_dir, paths.audio_dir, paths.transcript_dir, paths.status_dir):
            directory.mkdir(parents=True, exist_ok=True)
        atomic_write_json(paths.status_dir / "config.json", config.redacted_snapshot())
        return paths

    @property
    def source_metadata(self) -> Path:
        return self.source_dir / "metadata.json"

    def stage_state(self, stage: str) -> Path:
        return self.status_dir / f"{stage}.json"
