"""Typer command line interface for the standalone audio workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import typer

from .audio_extract import extract_audio
from .config import AudioJobConfig
from .export import ExportArtifacts, export_transcript
from .io import AudioJobPaths, atomic_write_json
from .models import AudioArtifact, TranscriptSegment
from .source import SourceArtifact, prepare_source, sha256_file
from .state import JobState
from .transcription import transcribe_with_metadata

app = typer.Typer(help="Extract and transcribe local media or a Twitch VOD without chat processing.")


def _paths(config: AudioJobConfig) -> tuple[AudioJobPaths, JobState]:
    paths = AudioJobPaths.create(config)
    return paths, JobState(paths)


def _source_from_metadata(paths: AudioJobPaths) -> SourceArtifact:
    metadata = json.loads(paths.source_metadata.read_text(encoding="utf-8"))
    return SourceArtifact(Path(metadata["path"]), str(metadata["kind"]), float(metadata.get("start_seconds") or 0))


def run_acquire(config: AudioJobConfig) -> SourceArtifact:
    paths, state = _paths(config)
    if config.media_path is not None:
        source = config.media_path.resolve()
        fingerprint = {"kind": "local", "path": str(source), "sha256": sha256_file(source)}
    else:
        fingerprint = {"kind": "vod", "vod_url": str(config.vod_url), "start_seconds": config.start_seconds, "end_seconds": config.end_seconds}
    if not state.should_run("acquire", fingerprint, [paths.source_metadata]):
        artifact = _source_from_metadata(paths)
        if artifact.path.is_file():
            return artifact
    state.start("acquire", fingerprint)
    try:
        artifact = prepare_source(config, paths)
        state.complete("acquire", fingerprint, [paths.source_metadata], skipped=config.media_path is not None, details={"kind": artifact.kind})
        return artifact
    except Exception as error:
        state.fail("acquire", fingerprint, error)
        raise


def _audio_from_metadata(paths: AudioJobPaths) -> AudioArtifact:
    payload = json.loads((paths.audio_dir / "metadata.json").read_text(encoding="utf-8"))
    return AudioArtifact(Path(payload["path"]), int(payload["sample_rate"]), int(payload["channels"]), float(payload["source_offset_seconds"]), payload["duration_seconds"])


def run_extract_audio(config: AudioJobConfig) -> AudioArtifact:
    paths, state = _paths(config)
    source = run_acquire(config)
    target = paths.audio_dir / "analysis.wav"
    fingerprint = {"source_sha256": sha256_file(source.path), "start_seconds": config.start_seconds, "end_seconds": config.end_seconds, "format": "16000-mono-wav"}
    if not state.should_run("audio", fingerprint, [target, paths.audio_dir / "metadata.json"]):
        return _audio_from_metadata(paths)
    state.start("audio", fingerprint)
    try:
        artifact = extract_audio(source.path, config, paths)
        state.complete("audio", fingerprint, [target, paths.audio_dir / "metadata.json"], details=artifact.to_dict())
        return artifact
    except Exception as error:
        state.fail("audio", fingerprint, error)
        raise


def _segments_from_file(path: Path) -> list[TranscriptSegment]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [TranscriptSegment(float(item["start_seconds"]), float(item["end_seconds"]), str(item["text"]), item.get("language"), item.get("average_log_probability")) for item in payload["segments"]]


def run_transcribe(config: AudioJobConfig) -> list[TranscriptSegment]:
    paths, state = _paths(config)
    audio = run_extract_audio(config)
    canonical = paths.transcript_dir / "canonical.json"
    fingerprint = {"audio_sha256": sha256_file(audio.path), "model_size": config.model_size, "language": config.language, "device": config.transcription_device, "compute_type": config.compute_type, "vad_filter": config.vad_filter}
    if not state.should_run("transcribe", fingerprint, [canonical, paths.transcript_dir / "run.json"]):
        return _segments_from_file(canonical)
    state.start("transcribe", fingerprint)
    try:
        result = transcribe_with_metadata(audio, config)
        payload = {"segments": [segment.to_dict() for segment in result.segments]}
        atomic_write_json(canonical, payload)
        atomic_write_json(paths.transcript_dir / "run.json", {"device": result.selection.device, "compute_type": result.selection.compute_type, "fallback_reason": result.selection.fallback_reason})
        state.complete("transcribe", fingerprint, [canonical, paths.transcript_dir / "run.json"], details={"segments": len(result.segments), "device": result.selection.device, "fallback_reason": result.selection.fallback_reason})
        return result.segments
    except Exception as error:
        state.fail("transcribe", fingerprint, error)
        raise


def run_export(config: AudioJobConfig) -> ExportArtifacts:
    paths, state = _paths(config)
    segments = run_transcribe(config)
    files = [paths.transcript_dir / name for name in ("transcript.json", "transcript.csv", "transcript.srt", "transcript.vtt")]
    fingerprint = {"canonical_sha256": sha256_file(paths.transcript_dir / "canonical.json"), "format": "json-csv-srt-vtt"}
    if not state.should_run("export", fingerprint, files):
        return ExportArtifacts(*files)
    state.start("export", fingerprint)
    try:
        artifacts = export_transcript(segments, paths)
        state.complete("export", fingerprint, files, details={"segments": len(segments)})
        return artifacts
    except Exception as error:
        state.fail("export", fingerprint, error)
        raise


def run_all(config: AudioJobConfig) -> ExportArtifacts:
    """Execute stages in order so a failure prevents all later work."""
    run_acquire(config)
    run_extract_audio(config)
    run_transcribe(config)
    return run_export(config)


def _load(path: Path) -> AudioJobConfig:
    return AudioJobConfig.from_file(path)


def _command(action: Callable[[AudioJobConfig], object], config_path: Path) -> None:
    try:
        action(_load(config_path))
    except Exception as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(1) from error


@app.command("acquire")
def acquire(config: Path = typer.Option(..., "--config", exists=True, readable=True)) -> None:
    _command(run_acquire, config)


@app.command("extract-audio")
def extract_audio_command(config: Path = typer.Option(..., "--config", exists=True, readable=True)) -> None:
    _command(run_extract_audio, config)


@app.command("transcribe")
def transcribe_command(config: Path = typer.Option(..., "--config", exists=True, readable=True)) -> None:
    _command(run_transcribe, config)


@app.command("export")
def export_command(config: Path = typer.Option(..., "--config", exists=True, readable=True)) -> None:
    _command(run_export, config)


@app.command("run")
def run(config: Path = typer.Option(..., "--config", exists=True, readable=True)) -> None:
    _command(run_all, config)
