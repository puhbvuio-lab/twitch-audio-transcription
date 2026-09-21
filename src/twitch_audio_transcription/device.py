"""Explicit device selection: CUDA is used only after a successful probe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import TranscriptionDevice


@dataclass(frozen=True)
class DeviceSelection:
    device: str
    compute_type: str
    fallback_reason: str | None = None


def default_cuda_probe() -> tuple[bool, str | None]:
    try:
        import ctranslate2  # type: ignore[import-not-found]

        supported = ctranslate2.get_supported_compute_types("cuda")
        if supported:
            return True, None
        return False, "CUDA has no supported compute types"
    except Exception as error:
        return False, f"CUDA probe failed: {error}"


def select_device(strategy: TranscriptionDevice, probe: Callable[[], tuple[bool, str | None]] = default_cuda_probe) -> DeviceSelection:
    if strategy == "cpu":
        return DeviceSelection("cpu", "int8")
    available, reason = probe()
    if available:
        return DeviceSelection("cuda", "float16")
    if strategy == "cuda":
        raise RuntimeError(reason or "CUDA is unavailable")
    return DeviceSelection("cpu", "int8", reason or "CUDA is unavailable; using CPU")
