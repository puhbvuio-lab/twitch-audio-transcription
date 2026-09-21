# Integrated audio workflow report

## Delivered scope

The standalone project now supports exactly one local-media or Twitch-VOD input
per job, with no runtime imports from the supplied reference copy or any chat,
CCV, visual, label, history, or Excel workflow.

- `io`, `state`: job-local `01_source`, `02_audio`, `03_transcript`, and
  `09_status` directories; redacted configuration snapshot; atomic JSON state;
  input fingerprints; artifact-aware resume checks.
- `source`: read-only local metadata and SHA-256 fingerprinting; fakeable
  yt-dlp adapter that writes only under `01_source`; source bounds forwarding.
  Local acquisition is recorded as skipped. Browser-cookie selectors are runtime
  only and downloader errors are deliberately sanitized before they can reach
  state or CLI output.
- `audio_extract`: fakeable FFmpeg command construction for deterministic
  16 kHz mono PCM WAV. The output starts at analysis time zero and metadata
  records the original source offset and duration.
- `device`, `transcription`: probe-gated CUDA selection, explicit CPU fallback
  reason, failure for explicitly unavailable CUDA, and one auto-mode CPU retry
  after a CUDA runtime error. Faster-Whisper remains a lazy runtime dependency;
  tests use fake engines. Engine output is canonical `TranscriptSegment` data.
- `export`: canonical transcript data produces JSON, CSV, SRT, and VTT with
  shared half-up millisecond rounding.
- `cli`: Typer `acquire`, `extract-audio`, `transcribe`, `export`, and `run`
  commands. `run` calls stages in order and stops at the first failure.
- README and JSON examples document installation, FFmpeg/yt-dlp prerequisites,
  output layout, privacy, resume behavior, CUDA fallback, and the excluded scope.

## Verification

The required final command was run from the build worktree:

```powershell
$env:PYTHONPATH='src'; D:\anaconda3\python.exe -m pytest -q --basetemp=.pytest-tmp
```

Result: **24 passed in 0.44s**.

The suite covers configuration, local source immutability, VOD bound/cookie
handling, atomic state resume behavior, FFmpeg command and timing contract,
device selection and runtime fallback, canonical segment conversion, all export
formats at the 0.999/1.000-second boundary, CLI failure ordering, and an offline
extract → transcribe → export smoke path.

## Limits / follow-up considerations

No real Twitch request, model download, CUDA probe, FFmpeg process, or yt-dlp
process was invoked during verification; this is intentional so the suite stays
offline and hardware-independent. Real execution therefore requires the
documented local executables and declared Python dependencies. The supplied
`upstream_reference/` directory was not imported or committed.
