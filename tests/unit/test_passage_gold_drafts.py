"""The AI-drafted passage gold cases are well formed, match the committed PDFs, and are honestly labelled as unverified drafts.

They are not the gold set: `passage_gold_v1.jsonl` stays empty until a person verifies cases (annotation-guidelines §5).
"""
import re
from pathlib import Path

import pytest

from ai.rag.evaluation.passage_gold import load_passage_gold, validate, verified_cases

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = ROOT / "datasets" / "evaluation" / "passage_gold_v1_drafts.jsonl"
PDFS = ROOT / "docs" / "research"


@pytest.fixture(scope="module")
def cases():
    return load_passage_gold(DRAFTS)


@pytest.fixture(scope="module")
def page_texts(cases):
    pytest.importorskip("fitz")
    from ai.rag.evaluation.propose_candidates import indexed_pages

    wanted = {e.document_id for c in cases for e in c.evidence}
    return {(f"FF-NTRS-{path.stem}", page["page"]): page["verbatim"]
            for path in sorted(PDFS.glob("*.pdf")) if f"FF-NTRS-{path.stem}" in wanted for page in indexed_pages(path)}


def test_the_drafts_pass_the_validator_against_the_committed_pdfs(cases, page_texts):
    assert validate(cases, page_texts=page_texts) == []


def test_every_draft_is_unverified_and_the_original_35_are_ai_drafts(cases):
    assert {c.status for c in cases} == {"draft"} and all(not c.verified_by for c in cases) and verified_cases(cases) == []
    first = [c for c in cases if int(c.gold_id.split("-")[1]) <= 35]
    assert len(first) == 35 and all("AI draft" in c.author for c in first)
    # Later numbers are questions a person added with `add_unanswerable`: their author is that person, never an AI.
    assert all(c.author and "AI draft" not in c.author and not c.answerable for c in cases if c not in first)


def test_the_set_has_the_mix_the_protocol_asks_for(cases):
    answerable = [c for c in cases if c.answerable]
    unanswerable = [c for c in cases if not c.answerable]
    assert len(answerable) >= 20 and len(unanswerable) / len(cases) >= 0.25
    assert {c.unanswerable_kind for c in unanswerable} == {"in_domain_not_in_corpus", "out_of_domain"}
    assert sum(c.unanswerable_kind == "in_domain_not_in_corpus" for c in unanswerable) > sum(c.unanswerable_kind == "out_of_domain" for c in unanswerable)


def test_questions_are_paraphrases_not_quotes_of_their_passage(cases):
    def words(text):
        return re.findall(r"[a-z0-9]+", text.lower())

    for case in cases:
        for ev in case.evidence:
            q, p = words(case.question), words(ev.text)
            runs = {tuple(q[i:i + 5]) for i in range(len(q) - 4)}
            copied = [r for r in runs if any(tuple(p[j:j + 5]) == r for j in range(len(p) - 4))]
            assert not copied, f"{case.gold_id} copies a 5-word run from its passage: {copied[0]}"


def test_no_passage_is_used_by_two_cases_and_a_case_lists_every_page_that_answers_it(cases):
    spans = [(e.document_id, e.page, e.char_start) for c in cases for e in c.evidence]
    assert len(spans) == len(set(spans)), "two cases use the same passage"
    # Eight drafts state their answer on more than one page (found with the verification sheet and a critical read); retrieving any
    # of those pages is a hit.
    multi = {c.gold_id: sorted({(e.document_id, e.page) for e in c.evidence}) for c in cases if len(c.evidence) > 1}
    assert set(multi) == {"PG-002", "PG-005", "PG-007", "PG-008", "PG-009", "PG-016", "PG-021", "PG-023"}
