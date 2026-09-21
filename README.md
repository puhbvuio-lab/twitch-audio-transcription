# Twitch Audio Transcription

This scaffold defines a JSON configuration contract for transcription jobs.

Each job specifies exactly one source: a local `media_path` or a Twitch `vod_url`.
Optional `start_seconds` and `end_seconds` select a positive-duration clip.
`browser_cookie_source` is a runtime-only browser profile hint and is omitted from
the redacted configuration snapshot.

The supported transcription devices are `auto`, `cuda`, and `cpu`.

Run the configuration tests with:

```powershell
python -m pytest
```

See the credential-free examples in `examples/`.
