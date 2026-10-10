import base64
import json
import secrets
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flame_api.config import Settings

MAX_RESPONSE_BYTES = 64 * 1024 * 1024
ARTIFACT_NAMES = {"preprocessed", "mask", "overlay"}


class HfCvError(Exception):
    pass


def analyze_image_on_hf(
    settings: Settings,
    image_bytes: bytes,
    *,
    media_type: str,
    mm_per_pixel: float | None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if settings.cv_provider != "hf_space" or settings.cv_hf_space_url is None:
        raise HfCvError("Hugging Face CV is not configured.")
    if media_type not in {"image/jpeg", "image/png"}:
        raise HfCvError("Hugging Face CV supports JPEG and PNG images only.")
    if len(image_bytes) > settings.max_upload_bytes:
        raise HfCvError("Image exceeds the configured upload limit.")

    boundary = secrets.token_hex(16)
    filename = "input.png" if media_type == "image/png" else "input.jpg"
    fields = []
    if mm_per_pixel is not None:
        fields.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="mm_per_pixel"\r\n\r\n'
            f"{mm_per_pixel}\r\n"
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
    if settings.cv_hf_token is not None:
        headers["Authorization"] = f"Bearer {settings.cv_hf_token.get_secret_value()}"
    request = Request(
        f"{settings.cv_hf_space_url.rstrip('/')}/api/analyze",
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=settings.cv_timeout_s) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise HfCvError(f"Hugging Face CV returned HTTP {exc.code}.") from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise HfCvError("Hugging Face CV could not be reached.") from exc

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
        if artifact_bytes > settings.max_upload_bytes * 8:
            raise HfCvError("Hugging Face CV artifacts exceeded the configured size limit.")
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HfCvError("Hugging Face CV returned a non-PNG artifact.")
        artifacts[name] = content
    if "preprocessed" not in artifacts:
        raise HfCvError("Hugging Face CV did not return the preprocessed image.")
    return analysis, artifacts
