from __future__ import annotations

import pytest

from twitch_audio_transcription.device import select_device


def test_auto_uses_cuda_only_after_successful_probe() -> None:
    selection = select_device("auto", lambda: (True, None))
    assert selection.device == "cuda"
    assert selection.fallback_reason is None


def test_auto_falls_back_to_cpu_with_probe_reason() -> None:
    selection = select_device("auto", lambda: (False, "CUDA driver unavailable"))
    assert selection.device == "cpu"
    assert selection.fallback_reason == "CUDA driver unavailable"


def test_explicit_cuda_raises_when_probe_fails() -> None:
    with pytest.raises(RuntimeError, match="CUDA driver unavailable"):
        select_device("cuda", lambda: (False, "CUDA driver unavailable"))
