# Twitch Audio Transcription

A standalone local-media or Twitch-VOD audio workflow. It extracts a deterministic
16 kHz mono WAV, transcribes it with Faster-Whisper, and writes one canonical
timeline as JSON, CSV, SRT, and VTT. It intentionally does not download or
analyze chat, CCV, visuals, labels, history, or Excel reports.

## Install

Python 3.11+, [FFmpeg](https://ffmpeg.org/) on `PATH`, and `yt-dlp` on `PATH`
are required for real media/VOD processing. Install the project dependencies,
then use either credential-free example as a starting point.

```powershell
python -m pip install -e .
python -m twitch_audio_transcription run --config examples/local-media-job.json
```

`media_path` and `vod_url` are mutually exclusive. A local input is opened only
for reading: no copy or modification is made. For VOD jobs, an optional
`browser_cookie_source` is used only while invoking yt-dlp; it is excluded from
snapshots, state, errors, and exports.

`start_seconds` and `end_seconds` select a positive-duration analysis interval.
The emitted transcript always begins at analysis time `00:00:00`, while audio
metadata preserves the source offset.

## Commands and outputs

```text
python -m twitch_audio_transcription acquire --config job.json
python -m twitch_audio_transcription extract-audio --config job.json
python -m twitch_audio_transcription transcribe --config job.json
python -m twitch_audio_transcription export --config job.json
python -m twitch_audio_transcription run --config job.json
```

Outputs are placed in `<output_dir>/<job_id>/`: `01_source/`, `02_audio/`,
`03_transcript/`, and `09_status/`. Each stage has an atomic fingerprinted state
record and will skip only when its inputs match and expected artifacts exist.
For a local source, `acquire` records metadata as `skipped`.

`transcription_device` accepts `auto`, `cuda`, or `cpu`. `auto` probes CUDA and
falls back to CPU with a stored reason; a CUDA runtime error receives one CPU
retry. An explicitly requested unavailable CUDA device fails rather than
pretending to use a GPU.

## Testing

Tests use fake FFmpeg, yt-dlp, and Whisper adapters; they do not access Twitch,
download models, require CUDA, or require a network connection.

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q --basetemp=.pytest-tmp
```
