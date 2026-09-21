from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from twitch_audio_transcription.cli import app


def test_run_stops_after_first_failed_stage(tmp_path: Path, monkeypatch) -> None:
    media = tmp_path / "source.wav"
    media.write_bytes(b"x")
    config = tmp_path / "job.json"
    config.write_text(json.dumps({"media_path": str(media), "output_dir": str(tmp_path / "out")}))
    calls: list[str] = []

    def failed(_config):
        calls.append("acquire")
        raise RuntimeError("acquire failed")

    monkeypatch.setattr("twitch_audio_transcription.cli.run_acquire", failed)
    monkeypatch.setattr("twitch_audio_transcription.cli.run_extract_audio", lambda _: calls.append("audio"))

    result = CliRunner().invoke(app, ["run", "--config", str(config)])

    assert result.exit_code != 0
    assert calls == ["acquire"]
