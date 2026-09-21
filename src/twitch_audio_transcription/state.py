"""Small atomic per-stage state machine for resumable jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .io import AudioJobPaths, atomic_write_json


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class JobState:
    def __init__(self, paths: AudioJobPaths) -> None:
        self.paths = paths

    def read(self, stage: str) -> dict[str, Any]:
        path = self.paths.stage_state(stage)
        if not path.exists():
            return {}
        try:
            import json

            loaded = json.loads(path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError):
            return {}

    def should_run(self, stage: str, fingerprint: dict[str, object], artifacts: Iterable[Path]) -> bool:
        prior = self.read(stage)
        return not (
            prior.get("status") in {"completed", "skipped"}
            and prior.get("fingerprint") == fingerprint
            and all(path.is_file() for path in artifacts)
        )

    def start(self, stage: str, fingerprint: dict[str, object]) -> None:
        atomic_write_json(self.paths.stage_state(stage), {"status": "running", "fingerprint": fingerprint, "started_at": _now()})

    def complete(self, stage: str, fingerprint: dict[str, object], artifacts: Iterable[Path], *, skipped: bool = False, details: dict[str, object] | None = None) -> None:
        atomic_write_json(
            self.paths.stage_state(stage),
            {
                "status": "skipped" if skipped else "completed",
                "fingerprint": fingerprint,
                "artifacts": [str(path) for path in artifacts],
                "details": details or {},
                "finished_at": _now(),
            },
        )

    def fail(self, stage: str, fingerprint: dict[str, object], error: Exception) -> None:
        atomic_write_json(
            self.paths.stage_state(stage),
            {"status": "failed", "fingerprint": fingerprint, "error": str(error), "finished_at": _now()},
        )
