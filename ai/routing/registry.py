"""Provider registry and the model manifest (``model_manifest.json``, the H-3 source of truth)."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from ai.providers.contracts.base import Provider

MANIFEST_PATH = Path(__file__).with_name("model_manifest.json")
_MANIFEST_FIELDS = {
    "model_id", "capability", "provider", "runtime", "name", "version", "quantization", "license",
    "source_url", "sha256", "size_bytes", "locality", "context_window", "status", "model_card", "notes",
    "ram_mb", "vram_mb", "cpu_only",
}


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, tuple[int, Provider]] = {}
        self._lock = threading.Lock()

    def register(self, provider: Provider, *, priority: int = 100) -> None:
        with self._lock:
            if provider.info.name in self._providers:
                raise ValueError(f"provider {provider.info.name!r} is already registered")
            self._providers[provider.info.name] = (priority, provider)

    def get(self, name: str) -> Provider | None:
        entry = self._providers.get(name)
        return entry[1] if entry else None

    def all(self) -> list[tuple[int, Provider]]:
        with self._lock:
            return sorted(self._providers.values(), key=lambda item: (item[0], item[1].info.name))


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """Read and validate the manifest. Unknown keys are an error so typos cannot hide."""
    entries = json.loads(path.read_text(encoding="utf-8"))["models"]
    seen: set[str] = set()
    for entry in entries:
        unknown = set(entry) - _MANIFEST_FIELDS
        if unknown:
            raise ValueError(f"{entry.get('model_id')}: unknown manifest keys {sorted(unknown)}")
        for required in ("model_id", "capability", "provider", "runtime", "name", "locality", "status"):
            if not entry.get(required):
                raise ValueError(f"{entry.get('model_id')}: missing {required}")
        if entry["locality"] not in {"local", "external"}:
            raise ValueError(f"{entry['model_id']}: locality must be local or external")
        if entry["model_id"] in seen:
            raise ValueError(f"duplicate model_id {entry['model_id']}")
        seen.add(entry["model_id"])
    return entries
