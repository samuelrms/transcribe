"""Device detection: CUDA when usable, CPU as the safe default."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeviceChoice:
    """A device plus the compute precision CTranslate2 accepts for it."""

    device: str
    compute_type: str
    label: str


CPU = DeviceChoice(device="cpu", compute_type="int8", label="CPU")
CUDA = DeviceChoice(device="cuda", compute_type="float16", label="GPU (CUDA)")


def cuda_device_count() -> int:
    """Number of NVIDIA GPUs visible to CTranslate2 (0 when unavailable)."""
    try:
        import ctranslate2
    except Exception:  # ctranslate2 missing or broken
        logger.debug("CTranslate2 unavailable for the CUDA check", exc_info=True)
        return 0
    try:
        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        # Missing driver, incompatible version, WSL without passthrough, etc.
        logger.debug("Could not query CUDA devices", exc_info=True)
        return 0


def cuda_available() -> bool:
    return cuda_device_count() > 0


def resolve_device(prefer_gpu: bool) -> DeviceChoice:
    """Pick the GPU only when the user asked for it and CUDA is usable."""
    if prefer_gpu and cuda_available():
        return CUDA
    if prefer_gpu:
        logger.info("GPU requested but no CUDA device available - using CPU.")
    return CPU
