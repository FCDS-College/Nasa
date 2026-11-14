"""The release gate: four states, no silent green, regression detection, exit codes (ai/rag/evaluation/gate.py)."""
import json

import pytest

from ai.rag.evaluation import gate
from ai.rag.evaluation.gate import FAIL, INCONCLUSIVE, NOT_MEASURED, PASS, decide, dig, evaluate, exit_code


def test_dig_follows_a_dotted_path_and_returns_none_when_a_step_is_missing():
    data = {"a": {"b": {"c": 3}}}
    assert dig(data, "a.b.c") == 3
    assert dig(data, "a.x.c") is None
    assert dig(data, "a.b.c.d") is None


@pytest.mark.parametrize(
    "value, ci, expected",
    [
        (0.90, (0.85, 0.95), PASS),             # even the worse end of the interval meets 0.80
        (0.88, (0.73, 0.98), INCONCLUSIVE),     # straddles the threshold: too few questions to say
        (0.32, (0.13, 0.55), FAIL),             # even the better end misses 0.70
    ],
)
def test_a_min_row_with_an_interval_is_judged_by_the_interval(value, ci, expected):
    threshold = 0.80 if expected != FAIL else 0.70
    assert decide(value, "min", threshold, ci, "ci") == expected


def test_a_max_row_is_judged_the_other_way_round():
    assert decide(0.02, "max", 0.05, (0.00, 0.04), "ci") == PASS
    assert decide(0.03, "max", 0.05, (0.01, 0.09), "ci") == INCONCLUSIVE
    assert decide(0.20, "max", 0.05, (0.10, 0.30), "ci") == FAIL


def test_a_ci_row_without_an_interval_is_inconclusive_not_a_point_pass():
    assert decide(0.99, "min", 0.8, None, "ci") == INCONCLUSIVE


def test_an_interval_is_derived_from_per_question_scores_when_the_report_has_none(tmp_path):
    path = _write(tmp_path, v=0.88, n=26, ver=26, per_question=[{"q": 1.0}] * 20 + [{"q": 0.0}] * 6)
    config = _config(path)
    config["rows"][0]["source"].update(ci=None, per_question="q", value="v")
    row = evaluate(config, tmp_path)[0]
    assert row["ci95"] is not None and row["ci95"][0] < 0.77 < row["ci95"][1]
    assert row["status"] == INCONCLUSIVE        # 20 of 26 cannot show 0.80 with a 26-question sample


def test_point_decisions_ignore_the_interval():
    assert decide(0.99, "min", 1.0, (0.9, 1.0), "point") == FAIL
    assert decide(1.0, "min", 1.0, None, "point") == PASS


def _config(path_value, **extra):
    row = {"id": "r", "title": "R", "direction": "min", "threshold": 0.8, "decision": "ci",
           "source": {"kind": "metric_report", "path": str(path_value), "value": "v", "ci": "ci", "n": "n", "verified": "ver"}, **extra}
    return {"version": "t", "rows": [row]}


def _write(tmp_path, **report):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_a_missing_report_is_not_measured_and_never_green(tmp_path):
    rows = evaluate(_config(tmp_path / "absent.json"), tmp_path)
    assert rows[0]["status"] == NOT_MEASURED
    assert exit_code(rows, enforce=True, release=False) == 0      # nothing failed
    assert exit_code(rows, enforce=False, release=True) == 1      # but a release needs every row to pass


def test_a_report_without_the_number_is_not_measured(tmp_path):
    path = _write(tmp_path, other=1)
    assert evaluate(_config(path), tmp_path)[0]["status"] == NOT_MEASURED


def test_unverified_labels_are_noted_and_block_a_release_pass(tmp_path):
    path = _write(tmp_path, v=0.95, ci=[0.9, 0.99], n=40, ver=0)
    row = evaluate(_config(path), tmp_path)[0]
    assert row["status"] == PASS and "not verified" in row["note"]
    release = evaluate(_config(path), tmp_path, release=True)[0]
    assert release["status"] == INCONCLUSIVE
    assert exit_code([release], enforce=False, release=True) == 1


def test_enforce_fails_on_a_failing_row_but_the_default_does_not(tmp_path):
    path = _write(tmp_path, v=0.3, ci=[0.1, 0.5], n=8, ver=8)
    rows = evaluate(_config(path), tmp_path)
    assert rows[0]["status"] == FAIL
    assert exit_code(rows, enforce=False, release=False) == 0
    assert exit_code(rows, enforce=True, release=False) == 1


def test_a_drop_of_more_than_two_points_against_the_baseline_is_a_regression(tmp_path):
    path = _write(tmp_path, v=0.90, ci=[0.88, 0.92], n=100, ver=100)
    worse = evaluate(_config(path), tmp_path, baseline={"r": 0.93})[0]
    assert worse["regression"] is True
    assert exit_code([worse], enforce=False, release=False) == 1   # always fatal
    within = evaluate(_config(path), tmp_path, baseline={"r": 0.91})[0]
    assert within["regression"] is False


def test_a_regression_on_a_max_row_is_a_rise(tmp_path):
    path = _write(tmp_path, v=0.08, ci=[0.06, 0.10], n=100, ver=100)
    row = evaluate(_config(path, direction="max", threshold=0.05), tmp_path, baseline={"r": 0.04})[0]
    assert row["regression"] is True


def test_informational_rows_never_decide_the_exit_code(tmp_path):
    path = _write(tmp_path, v=0.0, ci=[0.0, 0.0], n=1, ver=1)
    rows = evaluate(_config(path, informational=True), tmp_path)
    assert rows[0]["status"] == FAIL and rows[0]["informational"] is True
    assert exit_code(rows, enforce=True, release=True) == 0


def _junit(tmp_path, cases):
    body = "".join(f'<testcase classname="{c}" name="t{i}">{extra}</testcase>' for i, (c, extra) in enumerate(cases))
    path = tmp_path / "junit.xml"
    path.write_text(f'<testsuites><testsuite name="x">{body}</testsuite></testsuites>', encoding="utf-8")
    return path


def _contract_config():
    return {"version": "t", "rows": [{"id": "api", "title": "API", "direction": "min", "threshold": 1.0, "decision": "point",
                                      "source": {"kind": "junit", "classname_contains": ["test_contract_parity"]}}]}


def test_contract_tests_all_passing_is_a_pass(tmp_path):
    junit = _junit(tmp_path, [("apps.api.tests.test_contract_parity", ""), ("apps.api.tests.test_contract_parity", ""), ("other", "<failure/>")])
    row = evaluate(_contract_config(), tmp_path, junit)[0]
    assert row["status"] == PASS and row["n"] == 2


def test_a_failed_contract_test_fails_the_row_and_a_skipped_one_is_not_measured(tmp_path):
    failed = evaluate(_contract_config(), tmp_path, _junit(tmp_path, [("test_contract_parity", "<failure/>"), ("test_contract_parity", "")]))[0]
    assert failed["status"] == FAIL
    skipped = evaluate(_contract_config(), tmp_path, _junit(tmp_path, [("test_contract_parity", "<skipped/>")]))[0]
    assert skipped["status"] == NOT_MEASURED
    assert evaluate(_contract_config(), tmp_path, None)[0]["status"] == NOT_MEASURED


def test_the_committed_config_names_the_seven_gate_rows_and_valid_directions():
    config = json.loads(gate.CONFIG.read_text(encoding="utf-8"))
    ids = {row["id"] for row in config["rows"]}
    assert {"recall_at_5", "mrr", "unsupported_claim_rate", "pii_precision", "adversarial_refusal", "cv_iou", "api_contract"} <= ids
    for row in config["rows"]:
        assert row["direction"] in ("min", "max") and 0.0 <= row["threshold"] <= 1.0


def test_the_committed_baseline_and_reports_run_end_to_end(tmp_path, capsys):
    """Real committed reports: the CV row must FAIL decisively and the table must render."""
    code = gate.main(["--reports-dir", str(tmp_path), "--json", str(tmp_path / "out.json")])
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in out["rows"]}
    assert code == 0                                  # report mode never fails on a FAIL
    assert rows["cv_iou"]["status"] == FAIL
    assert rows["unsupported_claim_rate"]["status"] == NOT_MEASURED
    assert "| Row |" in capsys.readouterr().out
