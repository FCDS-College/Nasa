"""Rules for the passage-level gold set (audit finding E-2 / roadmap item 5). No question here is real data."""
import json

import pytest

from ai.rag.evaluation.passage_gold import (
    MIN_VERIFIED_FOR_REPORT, PassageCase, load_passage_gold, retrieval_report, validate, verified_cases,
)

PAGES = {("FF-NTRS-1", 3): "Flame speed was 3.2 cm/s at 0.1 atm in microgravity.", ("FF-NTRS-2", 1): "Oxygen fraction was 21 percent."}


def _case(gold_id="PG-001", *, split="dev", doc="FF-NTRS-1", page=3, start=0, end=24, text="Flame speed was 3.2 cm/s", answerable=True,
          kind=None, status="verified", author="a", verifiers=("b",), question="What was the flame speed?"):
    evidence = [{"document_id": doc, "page": page, "char_start": start, "char_end": end, "text": text}] if answerable else []
    return {"gold_id": gold_id, "split": split, "question": question, "answerable": answerable, "evidence": evidence,
            "question_type": "value_lookup", "unanswerable_kind": kind, "author": author, "verified_by": list(verifiers), "status": status}


def _cases(*raw):
    return [PassageCase.from_dict(r) for r in raw]


def _problems(*raw, **kwargs):
    return validate(_cases(*raw), **kwargs)


def test_a_clean_set_has_no_problems():
    cases = [_case("PG-001"), _case("PG-002", split="holdout", doc="FF-NTRS-2", page=1, start=0, end=15, text="Oxygen fraction"),
             _case("PG-003", answerable=False, kind="in_domain_not_in_corpus", split="validation", question="What was the soot yield?"),
             _case("PG-004", answerable=False, kind="out_of_domain", split="validation", question="Who won the cup?")]
    assert _problems(*cases, page_texts=PAGES) == []


def test_an_evidence_span_must_equal_the_page_text():
    problems = _problems(_case(text="Flame speed was 9.9 cm/s"), page_texts=PAGES)
    assert any("PG-001" in p and "does not match" in p for p in problems)


def test_an_answerable_case_needs_evidence_and_an_unanswerable_one_needs_a_kind():
    assert any("needs evidence" in p for p in _problems({**_case(), "evidence": []}))
    assert any("unanswerable_kind" in p for p in _problems(_case(answerable=False, kind=None)))
    assert any("unanswerable_kind" in p for p in _problems(_case(answerable=False, kind="whatever")))
    assert any("must not have" in p for p in _problems({**_case(), "unanswerable_kind": "out_of_domain"}))


def test_splits_must_not_share_a_document():
    problems = _problems(_case("PG-001", split="dev"), _case("PG-002", split="holdout"))
    assert any("FF-NTRS-1" in p and "dev" in p and "holdout" in p for p in problems)


def test_a_verified_case_needs_a_verifier_who_is_not_the_author():
    assert any("verifier" in p for p in _problems(_case(verifiers=())))
    assert any("verifier" in p for p in _problems(_case(author="a", verifiers=("a",))))
    assert _problems(_case(status="draft", verifiers=()), min_unanswerable_share=0.0) == []   # a draft needs no verifier


def test_too_few_unanswerable_questions_is_reported():
    assert any("unanswerable" in p for p in _problems(_case("PG-001"), _case("PG-002", doc="FF-NTRS-2", page=1, start=0, end=15, text="Oxygen fraction",
                                                                       split="dev")))


def test_only_cases_confirmed_by_someone_else_are_verified():
    cases = _cases(_case("PG-001"), _case("PG-002", status="draft", verifiers=()), _case("PG-003", verifiers=("a",)))
    assert [c.gold_id for c in verified_cases(cases)] == ["PG-001"]


def test_loading_reads_jsonl(tmp_path):
    path = tmp_path / "g.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in (_case("PG-001"), _case("PG-002", split="holdout", doc="FF-NTRS-2"))), encoding="utf-8")
    assert [c.gold_id for c in load_passage_gold(path)] == ["PG-001", "PG-002"]


def _verified_answerable(n):
    return [PassageCase.from_dict(_case(f"PG-{i:03d}", doc=f"FF-NTRS-{i}", page=1)) for i in range(n)]


def test_no_headline_number_without_enough_verified_cases():
    cases = _verified_answerable(MIN_VERIFIED_FOR_REPORT - 1)
    with pytest.raises(ValueError, match="verified"):
        retrieval_report(cases, {c.gold_id: [("FF-NTRS-0", 1)] for c in cases})


def test_page_level_retrieval_report_with_intervals():
    cases = _verified_answerable(MIN_VERIFIED_FOR_REPORT)
    rankings = {}
    for i, case in enumerate(cases):
        doc = case.evidence[0].document_id
        rankings[case.gold_id] = [(doc, 1)] if i % 4 else [("FF-NTRS-X", 9), (doc, 1)]    # every 4th is ranked second
    report = retrieval_report(cases, rankings, k=5)
    assert report["n"] == MIN_VERIFIED_FOR_REPORT and report["hit@1"] == pytest.approx(0.75)
    assert report["hit@5"] == 1.0 and report["mrr"] == pytest.approx(0.875)
    for key in ("hit@1", "hit@5", "mrr"):
        lo, hi = report["ci95"][key]
        assert lo <= report[key] <= hi
    assert report["ci95"]["hit@1"][1] > report["ci95"]["hit@1"][0]


def test_the_right_document_on_the_wrong_page_is_not_a_hit():
    cases = _verified_answerable(MIN_VERIFIED_FOR_REPORT)
    rankings = {c.gold_id: [(c.evidence[0].document_id, 99)] for c in cases}
    assert retrieval_report(cases, rankings)["hit@5"] == 0.0


# --- the JSON schema and the module must agree -------------------------------------------------------------------------

def test_the_schema_matches_the_module_and_the_gold_file_validates():
    from pathlib import Path

    import jsonschema

    from ai.rag.evaluation.passage_gold import SPLITS, STATUSES, UNANSWERABLE_KINDS

    schema = json.loads(Path("datasets/evaluation/passage_gold_v1.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    assert tuple(props["split"]["enum"]) == SPLITS
    assert tuple(props["status"]["enum"]) == STATUSES
    assert tuple(e for e in props["unanswerable_kind"]["enum"] if e is not None) == UNANSWERABLE_KINDS
    for line in Path("datasets/evaluation/passage_gold_v1.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            jsonschema.validate(json.loads(line), schema)
    # a well-formed case, built from the module's own test helper, is accepted by the schema
    jsonschema.validate(_case("PG-001"), schema)
