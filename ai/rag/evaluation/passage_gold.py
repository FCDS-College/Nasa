"""Passage-level gold set: schema rules, validation and page-level retrieval scoring with intervals.

Why: the existing gold sets cannot support the claims made on them (audit finding E-2). `retrieval_gold_v1` is 26
AI-authored questions with document-level labels and no unanswerable cases; `rag_gold` cites documents that are not in the
corpus. This module defines what a trustworthy set looks like and refuses to report numbers from one that is not:

* an evidence span is a character range of one page of one document, and its text must equal the page text there;
* answerable cases have evidence; unanswerable ones say whether the question is out of domain or in domain but not in
  the corpus (the dangerous kind: the dense similarity gate cannot catch it);
* splits are by DOCUMENT: no document appears in two splits;
* only cases marked `verified` by someone other than their author are scored, and no headline number is produced from
  fewer than `MIN_VERIFIED_FOR_REPORT` of them.

There is no data here. `datasets/evaluation/passage_gold_v1.jsonl` is empty until annotators write and verify cases
(docs/evaluation/annotation-guidelines.md §5).
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ai.rag.evaluation.stats import bootstrap_ci

SPLITS = ("dev", "validation", "holdout")
UNANSWERABLE_KINDS = ("out_of_domain", "in_domain_not_in_corpus")
STATUSES = ("draft", "verified")
# A floor below which a number would be mostly noise, not a sufficiency claim: report the interval whatever n is.
MIN_VERIFIED_FOR_REPORT = 20
RANK_DEPTH = 10


@dataclass(frozen=True)
class Evidence:
    document_id: str
    page: int
    char_start: int
    char_end: int
    text: str


@dataclass(frozen=True)
class PassageCase:
    gold_id: str
    split: str
    question: str
    answerable: bool
    evidence: tuple[Evidence, ...]
    question_type: str
    unanswerable_kind: str | None
    author: str
    verified_by: tuple[str, ...]
    status: str

    @classmethod
    def from_dict(cls, raw: Mapping) -> PassageCase:
        return cls(
            gold_id=raw["gold_id"], split=raw["split"], question=raw["question"], answerable=bool(raw["answerable"]),
            evidence=tuple(Evidence(e["document_id"], e["page"], e["char_start"], e["char_end"], e["text"]) for e in raw.get("evidence", [])),
            question_type=raw.get("question_type", ""), unanswerable_kind=raw.get("unanswerable_kind"),
            author=raw.get("author", ""), verified_by=tuple(raw.get("verified_by", [])), status=raw.get("status", "draft"),
        )


def load_passage_gold(path: str | Path) -> list[PassageCase]:
    return [PassageCase.from_dict(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def verified_cases(cases: list[PassageCase]) -> list[PassageCase]:
    """Cases confirmed by at least one person other than their author."""
    return [c for c in cases if c.status == "verified" and any(v and v != c.author for v in c.verified_by)]


def validate(cases: list[PassageCase], *, page_texts: Mapping[tuple[str, int], str] | None = None,
             min_unanswerable_share: float = 0.25) -> list[str]:
    """Every rule violation, as readable strings (empty list: the set is well formed). Never raises on bad data."""
    problems: list[str] = []
    seen: set[str] = set()
    documents: dict[str, set[str]] = {}
    for case in cases:
        label = case.gold_id
        if label in seen:
            problems.append(f"{label}: duplicate gold_id")
        seen.add(label)
        if case.split not in SPLITS:
            problems.append(f"{label}: split must be one of {SPLITS}, got {case.split!r}")
        if not case.question.strip():
            problems.append(f"{label}: empty question")
        if case.status not in STATUSES:
            problems.append(f"{label}: status must be one of {STATUSES}, got {case.status!r}")
        if case.status == "verified" and not any(v and v != case.author for v in case.verified_by):
            problems.append(f"{label}: a verified case needs a verifier other than the author")
        if case.answerable:
            if not case.evidence:
                problems.append(f"{label}: an answerable case needs evidence")
            if case.unanswerable_kind is not None:
                problems.append(f"{label}: an answerable case must not have an unanswerable_kind")
        else:
            if case.unanswerable_kind not in UNANSWERABLE_KINDS:
                problems.append(f"{label}: an unanswerable case needs unanswerable_kind in {UNANSWERABLE_KINDS}")
            if case.evidence:
                problems.append(f"{label}: an unanswerable case must not have evidence")
        for ev in case.evidence:
            documents.setdefault(ev.document_id, set()).add(case.split)
            if not 0 <= ev.char_start < ev.char_end:
                problems.append(f"{label}: evidence span {ev.char_start}:{ev.char_end} is empty or negative")
            elif page_texts is not None:
                page = page_texts.get((ev.document_id, ev.page))
                if page is None:
                    problems.append(f"{label}: no page text for {ev.document_id} p.{ev.page}")
                elif page[ev.char_start:ev.char_end] != ev.text:
                    problems.append(f"{label}: evidence text does not match {ev.document_id} p.{ev.page}[{ev.char_start}:{ev.char_end}]")
    for document, splits in sorted(documents.items()):
        if len(splits) > 1:
            problems.append(f"document {document} appears in splits {sorted(splits)}: split by document, not by question")
    if cases:
        unanswerable = sum(not c.answerable for c in cases)
        if unanswerable / len(cases) < min_unanswerable_share:
            problems.append(f"only {unanswerable} of {len(cases)} cases are unanswerable; at least {min_unanswerable_share:.0%} are needed")
    return problems


def retrieval_report(cases: list[PassageCase], rankings: Mapping[str, list[tuple[str, int]]], *, k: int = 5, seed: int = 0) -> dict:
    """Page-level hit@1, hit@k and MRR over the verified answerable cases, each with a 95% bootstrap interval.

    `rankings[gold_id]` is the retrieved (document_id, page) list, best first. The right document on the wrong page is a miss.
    """
    scored = [c for c in verified_cases(cases) if c.answerable]
    if len(scored) < MIN_VERIFIED_FOR_REPORT:
        raise ValueError(f"need at least {MIN_VERIFIED_FOR_REPORT} verified answerable cases to report, have {len(scored)}")
    missing = [c.gold_id for c in scored if c.gold_id not in rankings]
    if missing:
        raise ValueError(f"no ranking for {missing[:5]}")
    hits1, hitsk, rrs = [], [], []
    for case in scored:
        wanted = {(e.document_id, e.page) for e in case.evidence}
        first = next((i for i, hit in enumerate(rankings[case.gold_id][:RANK_DEPTH], start=1) if tuple(hit) in wanted), None)
        hits1.append(float(first == 1))
        hitsk.append(float(first is not None and first <= k))
        rrs.append(0.0 if first is None else 1.0 / first)
    series = {"hit@1": hits1, f"hit@{k}": hitsk, "mrr": rrs}
    return {"n": len(scored), **{name: sum(v) / len(v) for name, v in series.items()},
            "ci95": {name: list(bootstrap_ci(v, seed=seed)) for name, v in series.items()}}
