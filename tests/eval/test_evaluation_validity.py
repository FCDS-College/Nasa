"""The evaluation tooling must not report success it has not earned (audit finding E-1).

Each test names a defect that was verified in the code before it was fixed.
"""
import json

import pandas as pd
import pytest

from run_evaluation import run_evaluation_suite
from tests.eval.evaluator import evaluate_model
from tests.eval.master_pipeline import LLMJudge, parse_judge_verdict
from tests.eval.metrics import compute_mrr, compute_ndcg_at_k, compute_recall_at_k
from tests.eval.rag_connector import RAGConnector


# --- metrics: "nothing was expected" is not a perfect score --------------------------------------------------------

def test_recall_mrr_and_ndcg_are_undefined_when_no_evidence_is_expected():
    # Returning 1.0 let the 7 unanswerable/adversarial cases dominate the reported baseline.
    assert compute_recall_at_k(["DOC-1"], []) is None
    assert compute_mrr(["DOC-1"], []) is None
    assert compute_ndcg_at_k(["DOC-1"], []) is None


def test_metrics_are_unchanged_when_evidence_is_expected():
    assert compute_recall_at_k(["a", "b", "c"], ["b", "z"], k=3) == 0.5
    assert compute_mrr(["a", "b"], ["b"]) == 0.5
    assert compute_mrr(["a"], ["b"]) == 0.0


# --- judge: parse the verdict, do not substring-match it -----------------------------------------------------------

@pytest.mark.parametrize("reply,verdict", [
    ('{"is_faithful": true, "score": 0.9, "reason": "grounded"}', True),
    ('{"is_faithful": false, "score": 0.1, "reason": "unsupported"}', False),   # contains the word "faithful"
    ('```json\n{"is_faithful": false}\n```', False),
    ('{"is_faithful": "false"}', False),
    ('{"is_faithful": "true"}', True),
    ("The answer is faithful to the context.", None),                           # prose is not a verdict
    ('{"score": 1}', None),
    ("", None),
])
def test_parse_judge_verdict(reply, verdict):
    assert parse_judge_verdict(reply) is verdict


class _FakeModel:
    def __init__(self, text):
        self.text = text

    def generate_content(self, prompt):
        return type("Reply", (), {"text": self.text})()


def _judge_with_reply(text):
    judge = LLMJudge()
    judge.has_gemini, judge.model = True, _FakeModel(text)
    return judge


def test_an_unfaithful_verdict_is_not_reported_as_faithful():
    result = _judge_with_reply('{"is_faithful": false, "score": 0.0}').evaluate_faithfulness("q", "context", "answer about flame")
    assert result["is_hallucination_free"] is False and result["judge_mode"] == "gemini-api"


def test_an_unparseable_reply_falls_back_to_the_local_heuristic_and_says_so():
    result = _judge_with_reply("I cannot say.").evaluate_faithfulness("q", "context", "flame in microgravity")
    assert result["judge_mode"] == "local-fallback"


def test_the_judge_does_not_claim_a_domain_relevance_it_never_assessed():
    result = _judge_with_reply('{"is_faithful": true}').evaluate_faithfulness("q", "context", "answer")
    assert result["domain_relevant"] is None


# --- evaluator: no scores means "not evaluated", not "passed" ------------------------------------------------------

def test_a_dataset_without_score_columns_is_not_reported_as_passing(capsys):
    gold_cases = pd.DataFrame([{"case_id": "TC_1", "query": "q", "answerable": True}])
    assert evaluate_model(gold_cases) is False
    out = capsys.readouterr().out
    assert "passed the baseline" not in out and "NOT EVALUATED" in out


def test_scores_above_the_thresholds_still_pass():
    scored = pd.DataFrame([{"metrics.retrieval_relevance": 4.5, "metrics.faithfulness": 4.9, "metrics.citation_accuracy": 4.5}])
    assert evaluate_model(scored) is True


# --- connector: an API mode that cannot work must say so ------------------------------------------------------------

def test_api_mode_fails_loudly_instead_of_scoring_a_connection_error_as_an_answer():
    # /api/search is GET ?q=...; the connector POSTed JSON, swallowed the failure and returned it as the "answer".
    with pytest.raises(NotImplementedError, match="flame_retrieval_benchmark"):
        RAGConnector(mode="api").query("what is the flame speed?")


# --- runner: the report says what was evaluated and averages only what is defined ------------------------------------

def _gold(path, *cases):
    path.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cases), encoding="utf-8")


def _case(case_id, expected_ids):
    return {"case_id": case_id, "split": "dev", "query": "combustion in microgravity", "difficulty": "easy",
            "expected_evidence_ids": expected_ids,
            "expected_evidence": [{"locator": "NASA-TM-2024-0012", "text": "x"}] if expected_ids else []}


def test_the_report_names_the_system_it_evaluated_and_ignores_undefined_retrieval_scores(tmp_path):
    gold, out = tmp_path / "gold.jsonl", tmp_path / "report.json"
    _gold(gold, _case("A1", ["DOC-001-P15"]), _case("U1", []), _case("U2", []))
    run_evaluation_suite(gold, out, model_mode="mock")
    report = json.loads(out.read_text(encoding="utf-8"))

    assert report["evaluated_system"]["kind"] == "mock"
    assert "not Flame" in report["evaluated_system"]["note"]
    summary = report["metrics_summary"]
    assert summary["n_answerable"] == 1 and summary["n_unanswerable"] == 2
    assert summary["mean_recall@5"] == 1.0            # one answerable case, and the mock retrieves its page
    unanswerable = [r for r in report["detailed_results"] if r["case_id"].startswith("U")]
    assert all(r["retrieval_recall@5"] is None and r["mrr"] is None for r in unanswerable)


def test_a_dataset_with_no_answerable_case_has_no_mean_recall(tmp_path):
    gold, out = tmp_path / "gold.jsonl", tmp_path / "report.json"
    _gold(gold, _case("U1", []))
    run_evaluation_suite(gold, out, model_mode="mock")
    assert json.loads(out.read_text(encoding="utf-8"))["metrics_summary"]["mean_recall@5"] is None


# --- report rendering: handle undefined means, never present the mock as a measurement of Flame -----------------------

def test_rendered_report_handles_undefined_means_and_names_the_mock(tmp_path):
    from render_report import render_json_report_to_markdown

    report = {
        "evaluated_system": {"kind": "mock", "note": "Hard-coded outputs: this scores the evaluation harness, not Flame."},
        "caveats": ["Abstention correctness on unanswerable cases is not computed."],
        "provenance": {"timestamp": "2026-11-13T00:00:00+00:00", "git_commit": "abc", "dataset_sha256": "0" * 64},
        "metrics_summary": {"n_answerable": 0, "n_unanswerable": 3, "mean_recall@5": None, "mean_mrr": None, "mean_citation_f1": None},
        "thresholds": {"recall@5_target": 0.80, "mrr_target": 0.70, "citation_f1_target": 0.75},
        "total_evaluated": 3, "pass_count": 0, "fail_count": 3,
    }
    json_path = tmp_path / "report.json"
    json_path.write_text(json.dumps(report), encoding="utf-8")
    md_path = tmp_path / "docs" / "evaluation" / "reports" / "baseline.md"
    md_path.parent.mkdir(parents=True)

    assert render_json_report_to_markdown(json_path, md_path) is True

    markdown = md_path.read_text(encoding="utf-8")
    assert "n/a" in markdown and "not Flame" in markdown
    assert "38 NASA domain gold cases" not in markdown
    assert "Baseline Measured Value" not in markdown
    assert "not Flame" in (tmp_path / "docs" / "scorecard.html").read_text(encoding="utf-8")
