"""Load and validate portable transcription-job configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, model_validator

from .models import TranscriptionDevice


class AudioJobConfig(BaseModel):
    """A transcription job with exactly one input source."""

    media_path: Path | None = None
    vod_url: HttpUrl | None = None
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    browser_cookie_source: str | None = None
    transcription_device: TranscriptionDevice = "auto"

    @model_validator(mode="after")
    def validate_job(self) -> "AudioJobConfig":
        if (self.media_path is None) == (self.vod_url is None):
            raise ValueError("exactly one of media_path or vod_url must be configured")
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds <= self.start_seconds
        ):
            raise ValueError("end_seconds must be greater than start_seconds")
        if self.media_path is not None and not self.media_path.is_file():
            raise ValueError(f"media_path does not exist or is not a file: {self.media_path}")
        return self

    @classmethod
    def from_file(cls, path: Path) -> "AudioJobConfig":
        """Read a JSON job description from *path*."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def redacted_snapshot(self) -> dict[str, object]:
        """Return a serializable configuration view without runtime credentials."""
        return self.model_dump(mode="json", exclude={"browser_cookie_source"})
