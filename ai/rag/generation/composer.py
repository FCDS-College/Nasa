"""Grounded answer composer with citation validation and abstention.

Policy (v1.0.0):
  * Abstain (status=insufficient_evidence) when: the bundle is not "ok",
    there are zero evidence chunks, the best evidence score is below
    `min_top_score`, the model output is not valid JSON, or no claim
    survives validation.
  * Abstain (status=conflicting_evidence) when two retrieved chunks declare
    each other in `metadata["conflicts_with"]`.
  * Every cited id must be in the retrieved set; others are removed and
    reported as `citations_not_in_retrieved_evidence_removed`.
  * A claim with no valid citation is removed. If some claims survive but
    some were removed, status is `partially_supported`.
  * Causal wording on an observed/measured claim downgrades it to
    `inferred` (association is not causation).
  * The answer text is rebuilt from validated claims, never copied from the
    raw model output.
"""
from __future__ import annotations

import json
import re

from ai.interfaces import AnswerComposer, LLMProvider
from ai.rag.generation.models import (
    CLAIM_LABELS,
    STATUS_ANSWERED,
    STATUS_CONFLICTING,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    Claim,
    GroundedAnswer,
)
from ai.rag.prompts.registry import PromptRegistry, render_evidence_block, render_memory_block

CAUSAL_WORDS = re.compile(
    r"\b(causes?|caused|causing|leads? to|led to|results? in|because|due to|responsible for)\b",
    re.IGNORECASE,
)
INJECTION_PATTERNS = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|rules)|"
    r"disregard (the )?(system|previous)|you are now|reveal (your )?(system )?prompt|"
    r"act as (an? )?[a-z ]+ without restrictions)",
    re.IGNORECASE,
)
WARN_DROPPED = "citations_not_in_retrieved_evidence_removed"


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    return re.sub(r"\s*```$", "", text)


class GroundedAnswerComposer(AnswerComposer):
    """Builds a cited answer from an EvidenceBundle, validating citations and abstaining when evidence is missing, weak or conflicting.

    Args:
        llm: an LLMProvider.
        registry: PromptRegistry (default registry if omitted).
        min_top_score: minimum best-evidence score before answering (default 0.3, not calibrated).

    See docs/ai/grounded-generation.md."""

    def __init__(
        self,
        llm: LLMProvider,
        registry: PromptRegistry | None = None,
        min_top_score: float = 0.3,
    ):
        self.llm = llm
        self.registry = registry or PromptRegistry()
        self.min_top_score = min_top_score

    # ------------------------------------------------------------------
    def _versions(self, *prompt_ids: str) -> dict[str, str]:
        versions = {pid: self.registry.get(pid).version for pid in prompt_ids}
        versions["llm"] = f"{self.llm.name}@{self.llm.version}"
        return versions

    def _abstain(self, question: str, reason: str, warnings: list[str]) -> GroundedAnswer:
        msg = self.registry.get("insufficient_evidence").render(question=question, reason=reason)
        return GroundedAnswer(
            question=question,
            status=STATUS_INSUFFICIENT,
            answer=msg,
            warnings=warnings,
            abstention_reason=reason,
            versions=self._versions("insufficient_evidence"),
        )

    @staticmethod
    def detect_conflicts(chunks: list[dict]) -> list[str]:
        """Return chunk ids that declare a conflict with another retrieved chunk."""
        ids = {c["chunk_id"] for c in chunks}
        conflicting: set[str] = set()
        for c in chunks:
            for other in (c.get("metadata") or {}).get("conflicts_with", []):
                if other in ids:
                    conflicting.update({c["chunk_id"], other})
        return sorted(conflicting)

    # ------------------------------------------------------------------
    def compose(self, question: str, bundle, memory=None) -> GroundedAnswer:
        """Compose a cited answer from `bundle` (an EvidenceBundle).

        Args:
            question: the user question.
            bundle: EvidenceBundle with `.status` and `.evidence`.
            memory: optional list of memory records (context only).

        Returns:
            GroundedAnswer; never raises on bad model output (it abstains).
        """
        warnings: list[str] = []
        memory = list(memory or [])

        if bundle.status != "ok" or not bundle.evidence:
            return self._abstain(question, "no relevant evidence was retrieved", warnings)

        chunks = [c.model_dump() for c in bundle.evidence]

        top = max(c["score"] for c in chunks)
        if top < self.min_top_score:
            return self._abstain(
                question, f"best evidence score {top:.2f} is below the minimum {self.min_top_score:.2f}", warnings
            )

        conflict_ids = self.detect_conflicts(chunks)
        if conflict_ids:
            msg = self.registry.get("conflicting_evidence").render(
                question=question, evidence_ids=", ".join(conflict_ids)
            )
            return GroundedAnswer(
                question=question,
                status=STATUS_CONFLICTING,
                answer=msg,
                citations=[{"citation_id": f"C{i}", "chunk_id": cid} for i, cid in enumerate(conflict_ids, 1)],
                abstention_reason="retrieved sources contradict each other",
                versions=self._versions("conflicting_evidence"),
            )

        for c in chunks:
            if INJECTION_PATTERNS.search(c["text"]):
                warnings.append(f"possible_prompt_injection_in_evidence:{c['chunk_id']}")

        system = self.registry.get("system_scientific_qa")
        grounded = self.registry.get("grounded_answer")
        user_prompt = grounded.render(
            question=question,
            evidence_block=render_evidence_block(chunks),
            memory_block=render_memory_block(
                [{"id": m.id, "origin": m.origin, "text": m.text} for m in memory]
            ) or "(none)",
        )

        raw = self.llm.generate(system.template, user_prompt)
        try:
            payload = json.loads(_strip_fences(raw))
            raw_claims = payload["claims"]
            if not isinstance(raw_claims, list):
                raise TypeError("claims must be a list")
        except (ValueError, KeyError, TypeError):
            return self._abstain(question, "the model output was not valid structured JSON", warnings)

        by_id = {c["chunk_id"]: c for c in chunks}
        kept: list[Claim] = []
        dropped_ids: list[str] = []
        removed_claims = 0

        for item in raw_claims:
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                removed_claims += 1
                continue
            cited = item.get("evidence_ids") or []
            valid = [i for i in cited if i in by_id]
            bad = [i for i in cited if i not in by_id]
            if bad:
                dropped_ids.extend(bad)
            if not valid:
                removed_claims += 1
                continue

            label = item.get("label")
            if label not in CLAIM_LABELS:
                warnings.append("unknown_claim_label_downgraded_to_inferred")
                label = "inferred"
            if label in ("observed", "measured") and CAUSAL_WORDS.search(item["text"]):
                warnings.append("causal_wording_downgraded_to_inferred")
                label = "inferred"
            kept.append(Claim(text=item["text"].strip(), label=label, evidence_ids=valid))

        if dropped_ids:
            warnings.append(WARN_DROPPED)
        if removed_claims:
            warnings.append("claims_without_valid_evidence_removed")

        if not kept:
            return self._abstain(question, "no claim could be supported by retrieved evidence", warnings)

        citation_ids: dict[str, str] = {}
        citations: list[dict] = []
        for claim in kept:
            for eid in claim.evidence_ids:
                if eid not in citation_ids:
                    cid = f"C{len(citation_ids) + 1}"
                    citation_ids[eid] = cid
                    src = by_id[eid]
                    citations.append(
                        {
                            "citation_id": cid,
                            "chunk_id": eid,
                            "document_id": src["document_id"],
                            "document_version": src["document_version"],
                            "locator": src.get("locator"),
                        }
                    )
            claim.citation_ids = [citation_ids[e] for e in claim.evidence_ids]

        answer = "\n".join(
            f"- [{c.label}] {c.text} " + "".join(f"[{cid}]" for cid in c.citation_ids) for c in kept
        )

        return GroundedAnswer(
            question=question,
            status=STATUS_PARTIAL if removed_claims else STATUS_ANSWERED,
            answer=answer,
            claims=kept,
            citations=citations,
            warnings=sorted(set(warnings)),
            dropped_citation_ids=sorted(set(dropped_ids)),
            memory_used=[m.id for m in memory],
            versions=self._versions("system_scientific_qa", "grounded_answer"),
        )
