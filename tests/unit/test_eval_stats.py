"""Every reported retrieval number needs an interval (audit finding E-2: 26 questions cannot show a 0.05 effect)."""
import pytest

from ai.rag.evaluation.flame_retrieval_benchmark import score
from ai.rag.evaluation.stats import bootstrap_ci, compare_reports, paired_bootstrap_ci


def test_constant_values_have_a_degenerate_interval():
    assert bootstrap_ci([1.0, 1.0, 1.0, 1.0]) == (1.0, 1.0)


def test_the_interval_contains_the_mean_and_is_reproducible():
    values = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    lo, hi = bootstrap_ci(values, seed=3)
    assert lo <= sum(values) / len(values) <= hi and 0.0 <= lo < hi <= 1.0
    assert bootstrap_ci(values, seed=3) == (lo, hi)


def test_more_data_gives_a_narrower_interval():
    small = bootstrap_ci([1, 0, 1, 1, 1] * 4, seed=1)          # 20 observations, mean 0.8
    large = bootstrap_ci([1, 0, 1, 1, 1] * 40, seed=1)         # 200 observations, same mean
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_no_observations_is_an_error_not_a_number():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_identical_runs_differ_by_exactly_zero():
    assert paired_bootstrap_ci([1, 0, 1], [1, 0, 1]) == (0.0, 0.0)


def _report(label, rows):
    return {"label": label, "per_question": [{"id": i, "rr@10": rr, "hit@1": int(rr == 1.0)} for i, rr in rows]}


def test_compare_reports_pairs_questions_by_id_and_counts_wins():
    base = _report("base", [("Q1", 0.5), ("Q2", 1.0), ("Q3", 0.0), ("Q4", 1.0)])
    better = _report("better", [("Q1", 1.0), ("Q2", 1.0), ("Q3", 0.0), ("Q4", 0.5), ("Q9", 1.0)])   # Q9 is not in base
    result = compare_reports(base, better, metric="rr@10", seed=1)
    assert result["n"] == 4 and result["improved"] == 1 and result["worse"] == 1 and result["tied"] == 2
    assert result["delta"] == 0.0
    assert result["ci95"][0] <= result["delta"] <= result["ci95"][1]


def test_compare_reports_without_common_questions_is_an_error():
    with pytest.raises(ValueError):
        compare_reports(_report("a", [("Q1", 1.0)]), _report("b", [("Q2", 1.0)]), metric="rr@10")


def test_the_benchmark_reports_an_interval_for_every_headline_metric():
    gold = [{"id": f"Q{i}", "question": "q", "relevant": ["D1"]} for i in range(8)]
    runs = {f"Q{i}": (["D1"] if i < 6 else ["D9", "D1"]) for i in range(8)}
    result = score(gold, runs)
    assert set(result["ci95"]) == {"hit@1", "hit@3", "hit@5", "mrr@10", "recall@5"}
    lo, hi = result["ci95"]["hit@1"]
    assert lo <= result["hit@1"] <= hi and hi > lo, "with 6 of 8 hits the interval must have width"
