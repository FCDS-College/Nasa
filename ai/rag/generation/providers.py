"""LLM providers.

`ExtractiveLLMProvider` is an OFFLINE, deterministic baseline (no model). It
quotes the first sentence of the top evidence blocks as 'observed' claims. Use
it for tests and demos; swap in a real LLMProvider for production.
"""
from __future__ import annotations

import json
import re

from ai.interfaces import LLMProvider

_EVIDENCE_RE = re.compile(r'<evidence id="([^"]+)"[^>]*>\n(.*?)\n</evidence>', re.DOTALL)


class ExtractiveLLMProvider(LLMProvider):
    name = "extractive-baseline"
    version = "1.0.0"

    def __init__(self, max_claims: int = 2):
        self.max_claims = max_claims

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        claims = []
        for chunk_id, text in _EVIDENCE_RE.findall(user_prompt)[: self.max_claims]:
            text = text.replace("&lt;", "<").replace("&gt;", ">").strip()
            sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
            if sentence:
                claims.append({"text": sentence, "label": "observed", "evidence_ids": [chunk_id]})
        return json.dumps({"claims": claims})
