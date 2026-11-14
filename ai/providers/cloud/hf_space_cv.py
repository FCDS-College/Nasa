"""Hugging Face Space CV provider: Flame's own CV pipeline hosted on a GPU Space (external).

Blocked in offline_only mode. When it is unavailable the router falls back to the local
``flame_cv`` provider, which produces the same result shape, so a vision task never
degrades into a text-only model.
"""
from __future__ import annotations

import base64
import json
import secrets
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.vision import ImageAnalysisRequest, ImageAnalysisResponse

MAX_RESPONSE_BYTES = 64 * 1024 * 1024
ARTIFACT_NAMES = {"preprocessed", "mask", "overlay"}


class HfCvError(ProviderError):
    def __init__(self, message: str, code: ProviderErrorCode = ProviderErrorCode.INVALID_OUTPUT, **kwargs: Any) -> None:
        super().__init__(code, message, provider="hf_space", **kwargs)


def analyze_on_hf_space(
    *,
    base_url: str,
    token: str | None,
    timeout_s: float,
    max_upload_bytes: int,
    image_bytes: bytes,
    media_type: str,
    mm_per_pixel: float | None,
    camera_profile: str | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if media_type not in {"image/jpeg", "image/png"}:
        raise HfCvError("Hugging Face CV supports JPEG and PNG images only.", ProviderErrorCode.INVALID_REQUEST)
    if len(image_bytes) > max_upload_bytes:
        raise HfCvError("Image exceeds the configured upload limit.", ProviderErrorCode.INVALID_REQUEST)

    boundary = secrets.token_hex(16)
    filename = "input.png" if media_type == "image/png" else "input.jpg"
    fields = []
    if mm_per_pixel is not None:
        fields.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="mm_per_pixel"\r\n\r\n'
            f"{mm_per_pixel}\r\n"
        )
    if camera_profile is not None:
        fields.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="camera_profile"\r\n\r\n'
            f"{camera_profile}\r\n"
        )
    prefix = "".join(fields).encode("ascii")
    body = (
        prefix
        + f"--{boundary}\r\n".encode("ascii")
        + (
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: {media_type}\r\n\r\n"
        ).encode("ascii")
        + image_bytes
        + f"\r\n--{boundary}--\r\n".encode("ascii")
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{base_url.rstrip('/')}/api/analyze",
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise HfCvError(f"Hugging Face CV returned HTTP {exc.code}.", ProviderErrorCode.UNAVAILABLE, status_code=exc.code) from exc
    except URLError as exc:
        raise HfCvError("Hugging Face CV could not be reached.", ProviderErrorCode.UNAVAILABLE, request_sent=False) from exc
    except (TimeoutError, OSError) as exc:
        raise HfCvError("Hugging Face CV could not be reached.", ProviderErrorCode.TIMEOUT) from exc

    if len(response_body) > MAX_RESPONSE_BYTES:
        raise HfCvError("Hugging Face CV response exceeded the configured size limit.")
    try:
        decoded = json.loads(response_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HfCvError("Hugging Face CV returned invalid JSON.") from exc
    if not isinstance(decoded, dict):
        raise HfCvError("Hugging Face CV returned an invalid response.")
    analysis = decoded.get("analysis")
    encoded_artifacts = decoded.get("artifacts")
    if not isinstance(analysis, dict) or not isinstance(encoded_artifacts, dict):
        raise HfCvError("Hugging Face CV response is missing analysis or artifacts.")
    if not all(
        isinstance(analysis.get(section), dict)
        for section in ("preprocessing", "segmentation", "provenance")
    ):
        raise HfCvError("Hugging Face CV returned an incomplete analysis.")

    artifacts: dict[str, bytes] = {}
    artifact_bytes = 0
    for name, value in encoded_artifacts.items():
        if name not in ARTIFACT_NAMES or not isinstance(value, str):
            raise HfCvError("Hugging Face CV returned an invalid artifact.")
        try:
            content = base64.b64decode(value, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise HfCvError("Hugging Face CV returned invalid artifact data.") from exc
        artifact_bytes += len(content)
        if artifact_bytes > max_upload_bytes * 8:
            raise HfCvError("Hugging Face CV artifacts exceeded the configured size limit.")
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HfCvError("Hugging Face CV returned a non-PNG artifact.")
        artifacts[name] = content
    if "preprocessed" not in artifacts:
        raise HfCvError("Hugging Face CV did not return the preprocessed image.")
    return analysis, artifacts


class HfSpaceCvProvider:
    def __init__(self, *, base_url: str, token: str | None, timeout_s: float, max_upload_bytes: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s
        self._max_upload_bytes = max_upload_bytes
        self.info = ProviderInfo(
            name="hf_space", runtime="hf_space", locality=Locality.EXTERNAL,
            capabilities=frozenset({Capability.VISION}), model="flame_cv@hf_space",
            modalities=frozenset({"image"}),
        )

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            with urlopen(Request(f"{self._base_url}/", headers=headers), timeout=timeout_s) as response:
                state = "up" if 200 <= response.status < 300 else "down"
        except (HTTPError, URLError, TimeoutError, OSError):
            state = "down"
        return HealthStatus(state, round((time.perf_counter() - started) * 1000, 1), None if state == "up" else "unavailable")

    def analyze_image(self, request: ImageAnalysisRequest) -> ImageAnalysisResponse:
        analysis, remote = analyze_on_hf_space(
            base_url=self._base_url, token=self._token, timeout_s=self._timeout_s,
            max_upload_bytes=self._max_upload_bytes, image_bytes=request.image_path.read_bytes(),
            media_type=request.media_type, mm_per_pixel=request.mm_per_pixel,
            camera_profile=request.camera_profile,
        )
        analysis["provenance"]["inputUri"] = str(request.image_path)
        paths = {}
        for name, content in remote.items():
            path = request.work_dir / f"{name}.png"
            path.write_bytes(content)
            paths[name] = path
            if name == "preprocessed":
                analysis["preprocessing"]["derivedUri"] = str(path)
            elif name == "mask":
                analysis["segmentation"]["maskUri"] = str(path)
            elif name == "overlay":
                analysis["segmentation"]["overlayArtifactUri"] = str(path)
        version = analysis.get("provenance", {}).get("pipelineVersion")
        return ImageAnalysisResponse(analysis=analysis, provider="hf_space", pipeline_version=version, artifacts=paths)
