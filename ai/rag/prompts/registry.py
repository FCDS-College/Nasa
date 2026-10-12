"""Versioned prompt registry.

One JSON file per prompt in `library/`, each with id, version, purpose,
model capability, input variables, output schema and template. The content
hash (sha256 of template + output_schema) is stored in the file and verified
on load, so a prompt cannot change without a version/hash bump.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

LIBRARY_DIR = Path(__file__).parent / "library"
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def compute_hash(template: str, output_schema: dict | None) -> str:
    payload = json.dumps(
        {"template": template, "output_schema": output_schema},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Prompt(BaseModel):
    id: str
    version: str
    purpose: str
    model_capability: str = "instruction-following, JSON output"
    input_variables: list[str] = Field(default_factory=list)
    output_schema: dict | None = None
    template: str
    content_hash: str = ""
    approved_by_eval_run: str | None = None
    path: str = ""

    def render(self, **variables: str) -> str:
        """Fill `{{name}}` placeholders.

        Raises:
            KeyError: a declared input variable was not supplied.
            ValueError: an unknown variable was supplied.
        """
        missing = [v for v in self.input_variables if v not in variables]
        if missing:
            raise KeyError(f"missing prompt variables: {missing}")
        unknown = [v for v in variables if v not in self.input_variables]
        if unknown:
            raise ValueError(f"unknown prompt variables: {unknown}")
        text = self.template
        for name, value in variables.items():
            text = text.replace("{{" + name + "}}", str(value))
        return text


class PromptRegistry:
    def __init__(self, library_dir: Path | str = LIBRARY_DIR):
        self._prompts: dict[tuple[str, str], Prompt] = {}
        self._load(Path(library_dir))

    def _load(self, directory: Path) -> None:
        for file in sorted(directory.glob("*.json")):
            data = json.loads(file.read_text(encoding="utf-8"))
            prompt = Prompt(**data, path=str(file.name))
            if not _SEMVER.match(prompt.version):
                raise ValueError(f"{file.name}: version must be semver, got {prompt.version}")
            actual = compute_hash(prompt.template, prompt.output_schema)
            if prompt.content_hash and prompt.content_hash != actual:
                raise ValueError(
                    f"{file.name}: content changed without updating version/hash "
                    f"(stored {prompt.content_hash[:12]}, actual {actual[:12]})"
                )
            prompt.content_hash = actual
            key = (prompt.id, prompt.version)
            if key in self._prompts:
                raise ValueError(f"duplicate prompt {key}")
            self._prompts[key] = prompt

    def get(self, prompt_id: str, version: str | None = None) -> Prompt:
        """Return a prompt by id (latest version if `version` is None).

        Raises:
            KeyError: unknown id/version.
        """
        if version is not None:
            return self._prompts[(prompt_id, version)]
        versions = [p for (pid, _), p in self._prompts.items() if pid == prompt_id]
        if not versions:
            raise KeyError(prompt_id)
        return max(versions, key=lambda p: tuple(int(x) for x in p.version.split(".")))

    def all(self) -> list[Prompt]:
        return sorted(self._prompts.values(), key=lambda p: (p.id, p.version))

    def table(self) -> str:
        """Markdown table of every prompt (for docs; generated, not typed)."""
        lines = [
            "| ID | Version | Purpose | Inputs | File | Hash |",
            "|---|---|---|---|---|---|",
        ]
        for p in self.all():
            lines.append(
                f"| {p.id} | {p.version} | {p.purpose} | {', '.join(p.input_variables)} "
                f"| `{p.path}` | `{p.content_hash[:12]}` |"
            )
        return "\n".join(lines)


def render_evidence_block(chunks: list[dict]) -> str:
    """Wrap evidence in <evidence> tags, neutralising tag injection.

    Each chunk dict needs `chunk_id`, `text`, and optionally `document_id`,
    `document_version`, `locator`. Any '<' inside the evidence text is
    escaped so a document cannot close the tag and smuggle instructions.
    """
    blocks = []
    for c in chunks:
        safe_text = str(c["text"]).replace("<", "&lt;").replace(">", "&gt;")
        attrs = (
            f'id="{c["chunk_id"]}" document="{c.get("document_id", "")}" '
            f'version="{c.get("document_version", "")}"'
        )
        loc = c.get("locator")
        if loc:
            attrs += f' locator="{json.dumps(loc, sort_keys=True).replace(chr(34), chr(39))}"'
        blocks.append(f"<evidence {attrs}>\n{safe_text}\n</evidence>")
    return "\n".join(blocks)


def render_memory_block(items: list[dict]) -> str:
    """Wrap session memory in <memory> tags (never mixed into <evidence>)."""
    blocks = []
    for m in items:
        safe = str(m["text"]).replace("<", "&lt;").replace(">", "&gt;")
        blocks.append(f'<memory id="{m["id"]}" origin="{m["origin"]}">\n{safe}\n</memory>')
    return "\n".join(blocks)
