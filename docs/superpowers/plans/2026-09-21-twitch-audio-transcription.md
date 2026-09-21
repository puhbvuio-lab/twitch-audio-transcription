# Twitch Audio Transcription Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, resumable local-media or Twitch-VOD audio extraction and Faster-Whisper transcription project.

**Architecture:** A source stage validates a local file or obtains a VOD, an FFmpeg stage creates deterministic analysis audio, and a transcription adapter produces canonical segments that one exporter renders to JSON/CSV/SRT/VTT. Each stage uses a redacted config fingerprint and atomic state files, so GPU/CPU fallback and retries are explicit and safe.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, FFmpeg, yt-dlp, Faster-Whisper, pytest.

**Spec:** `D:\twitch-audio-transcription\docs\superpowers\specs\2026-09-21-twitch-audio-transcription-design.md`

## Global Constraints

- The project is self-contained and has no import, config, output, or command dependency on any chat or prior-analysis project.
- Input is exactly one of `media_path` or `vod_url`; a local source is read-only.
- VOD boundaries apply to generated analysis audio and exports; all transcript formats use the same canonical segment timings.
- `auto` device mode detects usable CUDA first and reports any CPU fallback; it never claims GPU processing without a successful probe.
- No source credentials, cookies, tokens, or secrets may enter snapshots, logs, errors, or export files.
- Tests use fake transcribers and short fixtures; no model downloads, real VOD downloads, GPU, or network are required.

## Review Focus

- Both `media_path` and `vod_url` set at once must fail before any download or file operation (Task 1).
- A local video must remain byte-for-byte untouched; only output folders may be written (Task 2).
- FFmpeg output must be 16 kHz mono WAV and trim timestamps must be relative to the requested analysis interval (Task 4).
- CUDA probe or runtime failure must leave a human-readable reason and deliberately run CPU rather than a hanging `running` state (Task 5).
- JSON, CSV, SRT, and VTT timings must represent the same canonical segments including millisecond rounding boundaries (Task 6).

---

## File Structure

```text
twitch-audio-transcription/
  pyproject.toml
  README.md
  examples/local-media-job.json  examples/vod-job.json
  src/twitch_audio_transcription/
    __init__.py  __main__.py  cli.py  config.py  models.py  state.py  io.py
    source.py  audio_extract.py  device.py  transcription.py  export.py
  tests/
    conftest.py  test_config.py  test_state.py  test_source.py
    test_audio_extract.py  test_device.py  test_transcription.py
    test_export.py  test_cli.py  test_smoke.py
```

### Task 1: Scaffold and input configuration contract

**Files:**
- Create: `pyproject.toml`, `README.md`, `examples/local-media-job.json`, `examples/vod-job.json`
- Create: `src/twitch_audio_transcription/__init__.py`, `src/twitch_audio_transcription/config.py`, `src/twitch_audio_transcription/models.py`
- Test: `tests/test_config.py`

**Interfaces:** `AudioJobConfig.from_file(path: Path) -> AudioJobConfig`; `redacted_snapshot() -> dict[str, object]`.

- [ ] Write failing tests for neither/both sources, missing local path, reversed bounds, allowed `auto/cuda/cpu`, and cookie redaction.
- [ ] Run `pytest tests/test_config.py -v`; expect failure.
- [ ] Implement Pydantic validation and redacted snapshots, plus dependency declarations and credential-free examples.
- [ ] Run `pytest tests/test_config.py -v`; expect PASS.

### Task 2: Job paths, safe state, and local-source policy

**Files:**
- Create: `src/twitch_audio_transcription/io.py`, `src/twitch_audio_transcription/state.py`, `tests/test_state.py`, `tests/test_source.py`

**Interfaces:** `AudioJobPaths.create(config) -> AudioJobPaths`; project-local `should_run/start/complete/fail` state interface.

- [ ] Write failing tests for directory creation, complete-stage skip, changed-input rerun, and a local-file SHA-256 unchanged after source preparation.
- [ ] Run `pytest tests/test_state.py tests/test_source.py -v`; expect failure.
- [ ] Implement atomic state writes, source fingerprints, and read-only local-source metadata capture; never copy a local source.
- [ ] Run the two test files; expect PASS.

### Task 3: VOD download adapter

**Files:**
- Create: `src/twitch_audio_transcription/source.py`
- Modify: `tests/test_source.py`

**Interfaces:** `VodDownloader.download(vod_url, target_dir, start_seconds, end_seconds, cookie_source) -> Path`; `prepare_source(config, paths, downloader) -> Path`.

- [ ] Add failing fake-downloader tests for URL bounds forwarding, runtime-only cookies, download metadata, and local source `acquire` skip.
- [ ] Run `pytest tests/test_source.py -v`; expect failure.
- [ ] Implement a yt-dlp-backed adapter writing media and metadata only beneath `01_source`.
- [ ] Run `pytest tests/test_source.py -v`; expect PASS.

### Task 4: Deterministic FFmpeg audio extraction

**Files:**
- Create: `src/twitch_audio_transcription/audio_extract.py`
- Test: `tests/test_audio_extract.py`

**Interfaces:** `extract_audio(source: Path, config, paths, runner) -> AudioArtifact` with WAV path, sample rate, channels, source offset, and duration.

- [ ] Write failing fake-runner tests for bounds, 16 kHz mono output command construction, and output-location rules.
- [ ] Run `pytest tests/test_audio_extract.py -v`; expect failure.
- [ ] Implement FFmpeg invocation with `-ar 16000 -ac 1` and metadata persistence; first output sample is analysis time 0.
- [ ] Run `pytest tests/test_audio_extract.py -v`; expect PASS.

### Task 5: Device selection and Faster-Whisper adapter

**Files:**
- Create: `src/twitch_audio_transcription/device.py`, `src/twitch_audio_transcription/transcription.py`
- Test: `tests/test_device.py`, `tests/test_transcription.py`

**Interfaces:** `select_device(strategy, probe) -> DeviceSelection`; `transcribe(audio, config, engine) -> list[TranscriptSegment]`.

- [ ] Write failing tests for `auto` CUDA success, failed CUDA probe CPU fallback with reason, explicit unavailable CUDA error, and fake-engine segment conversion.
- [ ] Run `pytest tests/test_device.py tests/test_transcription.py -v`; expect failure.
- [ ] Implement device probing and Faster-Whisper integration; a runtime CUDA exception in `auto` retries once on CPU and persists the reason.
- [ ] Run the two test files; expect PASS.

### Task 6: Canonical transcript exporters and CLI

**Files:**
- Create: `src/twitch_audio_transcription/export.py`, `src/twitch_audio_transcription/cli.py`, `src/twitch_audio_transcription/__main__.py`
- Test: `tests/test_export.py`, `tests/test_cli.py`

**Interfaces:** `export_transcript(segments, paths) -> ExportArtifacts` containing JSON, CSV, SRT and VTT; CLI commands `acquire`, `extract-audio`, `transcribe`, `export`, `run` accept `--config PATH`.

- [ ] Write failing tests for one canonical segment rendered identically across formats at 0.999/1.000-second boundaries and CLI stop-on-failure ordering.
- [ ] Run `pytest tests/test_export.py tests/test_cli.py -v`; expect failure.
- [ ] Implement canonical JSON then derive CSV/SRT/VTT from it; orchestrate stages through Typer and state checks.
- [ ] Run `pytest tests/test_export.py tests/test_cli.py -v`; expect PASS.

### Task 7: Standalone documentation and offline smoke test

**Files:**
- Modify: `README.md`, `examples/local-media-job.json`, `examples/vod-job.json`
- Create: `tests/fixtures/tone.wav`, `tests/test_smoke.py`

- [ ] Write a failing smoke test using a local fixture and fake transcriber, running extract → transcribe → export without network or GPU.
- [ ] Run `pytest tests/test_smoke.py -v`; expect failure.
- [ ] Document installation, input options, FFmpeg prerequisite, GPU fallback, retry, outputs, privacy, and chat exclusion.
- [ ] Run `pytest -q`; expect PASS.
