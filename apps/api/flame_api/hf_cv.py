"""Compatibility shim: the Hugging Face Space client now lives in ``ai/providers/cloud/hf_space_cv.py``."""
from typing import Any

from ai.providers.cloud.hf_space_cv import ARTIFACT_NAMES, MAX_RESPONSE_BYTES, HfCvError, analyze_on_hf_space
from flame_api.config import Settings

__all__ = ["ARTIFACT_NAMES", "MAX_RESPONSE_BYTES", "HfCvError", "analyze_image_on_hf"]


def analyze_image_on_hf(
    settings: Settings,
    image_bytes: bytes,
    *,
    media_type: str,
    mm_per_pixel: float | None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if settings.cv_provider != "hf_space" or settings.cv_hf_space_url is None:
        raise HfCvError("Hugging Face CV is not configured.")
    return analyze_on_hf_space(
        base_url=settings.cv_hf_space_url,
        token=settings.cv_hf_token.get_secret_value() if settings.cv_hf_token is not None else None,
        timeout_s=settings.cv_timeout_s,
        max_upload_bytes=settings.max_upload_bytes,
        image_bytes=image_bytes,
        media_type=media_type,
        mm_per_pixel=mm_per_pixel,
    )
