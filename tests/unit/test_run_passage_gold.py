"""Runner that scores the verified passage gold through /api/search, compares two runs and calibrates an abstention threshold."""
import pytest

from ai.rag.evaluation.passage_gold import PassageCase
from ai.rag.evaluation.run_passage_gold import auc, calibrate, compare_runs, rankings_from_body, run


def _case(gold_id, *, answerable=True, doc="FF-NTRS-1", page=1, verified=True, split="dev"):
    evidence = [{"document_id": doc, "page": page, "char_start": 0, "char_end": 5, "text": "hello"}] if answerable else []
    return PassageCase.from_dict({
        "gold_id": gold_id, "split": split, "question": f"A question about {gold_id} that is long enough", "answerable": answerable,
        "evidence": evidence, "question_type": "other", "unanswerable_kind": None if answerable else "out_of_domain", "author": "Author",
        "verified_by": ["Verifier"] if verified else [], "status": "verified" if verified else "draft"})


def _body(*hits, score=0.03, mode="hybrid", reranking="applied"):
    return {"results": [{"source": {"source_id": doc}, "locator": {"page": page}, "score": hit_score}
                        for (doc, page), hit_score in zip(hits, [score] * len(hits))],
            "retrieval": {"mode": mode, "reranking": {"status": reranking}}}


def test_rankings_come_from_source_id_and_page_and_keep_the_best_first():
    body = _body(("FF-NTRS-2", 3), ("FF-NTRS-1", 1), ("FF-NTRS-1", 1))
    assert rankings_from_body(body) == [("FF-NTRS-2", 3), ("FF-NTRS-1", 1)]       # a repeated page counts once; a hit without a page is dropped
    assert rankings_from_body({"results": [{"source": {"source_id": "X"}, "locator": None}], "retrieval": {}}) == []


def _cases(n_answerable=20, n_unanswerable=8):
    return [_case(f"PG-{i:03d}", doc=f"FF-NTRS-{i}", page=1) for i in range(1, n_answerable + 1)] + \
           [_case(f"PG-{100 + i:03d}", answerable=False) for i in range(n_unanswerable)]


def test_a_run_scores_verified_answerable_cases_at_page_level_and_records_unanswerable_top_scores():
    cases = _cases()

    def fetch(question):       # right page first for answerable questions, junk with a low score for unanswerable ones
        for case in cases:
            if case.question == question and case.answerable:
                return _body((case.evidence[0].document_id, 1), score=0.0328)
        return _body(("FF-NTRS-999", 7), score=0.0164)

    report = run(cases, fetch, label="baseline")
    assert report["label"] == "baseline" and report["n_answerable"] == 20 and report["n_unanswerable"] == 8
    assert report["retrieval"]["hit@1"] == 1.0 and report["retrieval"]["ci95"]["hit@1"][0] > 0.8
    assert {q["top_score"] for q in report["per_question"] if not q["answerable"]} == {0.0164}


def test_a_run_refuses_to_report_with_too_few_verified_cases_and_ignores_drafts():
    with pytest.raises(ValueError, match="at least 20"):
        run(_cases(n_answerable=19), lambda q: _body(), label="x")
    drafts = [_case(f"PG-{i:03d}", doc=f"FF-NTRS-{i}", verified=False) for i in range(1, 30)]
    with pytest.raises(ValueError, match="at least 20"):
        run(drafts, lambda q: _body(), label="x")


def test_the_right_document_on_the_wrong_page_is_a_miss():
    cases = _cases()
    report = run(cases, lambda q: _body(("FF-NTRS-1", 99)), label="wrong-page")
    assert report["retrieval"]["hit@5"] <= 0.0


def test_compare_runs_pairs_questions_and_reports_whether_the_difference_is_shown():
    cases = _cases()
    good = run(cases, lambda q: _body(*[(c.evidence[0].document_id, 1) for c in cases if c.answerable and c.question == q]), label="good")
    bad = run(cases, lambda q: _body(("FF-NTRS-999", 1)), label="bad")
    result = compare_runs(bad, good)
    assert result["n"] == 20 and result["delta"] > 0.9 and result["ci95"][0] > 0 and result["difference_shown"] is True
    same = compare_runs(good, good)
    assert same["delta"] == 0 and same["difference_shown"] is False


def test_auc_is_the_chance_that_an_answerable_question_outscores_an_unanswerable_one():
    assert auc([0.9, 0.8], [0.1, 0.2]) == 1.0 and auc([0.1], [0.9]) == 0.0 and auc([0.5], [0.5]) == 0.5


def test_calibration_proposes_a_threshold_only_from_enough_verified_cases_and_never_writes_settings():
    cases = _cases()

    def fetch(question):
        hit = next((c for c in cases if c.question == question), None)
        if hit.answerable:
            return _body((hit.evidence[0].document_id, 1), score=0.0328)
        return _body(("FF-NTRS-999", 1), score=0.0164)

    report = run(cases, fetch, label="cal")
    result = calibrate(report)
    assert result["auc"]["value"] == 1.0 and 0.0164 < result["candidate_threshold"] <= 0.0328
    assert result["answerable_abstained"] == 0.0 and result["unanswerable_abstained"] == 1.0
    assert "FLAME_CHAT" not in str(result) and result["note"].startswith("A candidate")
    few = run(_cases(n_unanswerable=8), fetch, label="cal")
    few["per_question"] = [q for q in few["per_question"] if q["answerable"] or q["id"] < "PG-103"]     # only 3 unanswerable remain
    with pytest.raises(ValueError, match="unanswerable"):
        calibrate(few)


def test_a_run_refuses_a_gold_file_that_breaks_its_own_rules(tmp_path):
    cases = _cases(n_answerable=20, n_unanswerable=0)          # 0 % unanswerable: the set is incomplete
    with pytest.raises(ValueError, match="unanswerable"):
        run(cases, lambda q: _body(), label="partial")
