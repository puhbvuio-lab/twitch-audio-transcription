"""Shared type aliases for audio transcription configuration."""

from typing import Literal

TranscriptionDevice = Literal["auto", "cuda", "cpu"]
