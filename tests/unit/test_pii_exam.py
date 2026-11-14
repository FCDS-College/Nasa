"""The PII exam: the file is sound, the arithmetic is right, and the committed masker's weaknesses are on record."""
import pytest

from ai.rag.evaluation import run_pii_exam as exam


def test_the_committed_exam_file_validates():
    cases = exam.load()
    assert exam.validate(cases) == []
    assert len(cases) >= 40
    langs = {c["lang"] for c in cases}
    assert langs == {"en", "ar"}
    assert all(c["provenance"]["verified"] is False for c in cases), "AI-drafted: nobody has verified it yet"


def test_validate_catches_a_string_that_is_not_in_the_text_and_duplicates():
    good = {"id": "A", "lang": "en", "kind": "k", "text": "mail a@b.co now", "pii": ["a@b.co"], "keep": ["now"], "provenance": {}}
    bad = {**good, "id": "A", "pii": ["zzz"]}
    problems = exam.validate([good, bad])
    assert any("not in the text" in p for p in problems) and any("duplicate" in p for p in problems)


def test_scoring_counts_hits_misses_and_damage():
    cases = [
        {"id": "1", "lang": "en", "kind": "email", "text": "x a@b.co y", "pii": ["a@b.co"], "keep": ["x"], "provenance": {}},
        {"id": "2", "lang": "en", "kind": "phone", "text": "call 111 now", "pii": ["111"], "keep": ["now"], "provenance": {}},
    ]
    # a masker that hides the e-mail, leaves the phone number and removes the harmless word "now"
    report = exam.run(cases, lambda text: text.replace("a@b.co", "[E]").replace("now", ""))
    assert (report["n_pii"], report["misses"], report["false_positives"]) == (2, 1, 1)
    assert report["precision"] == 0.5 and report["miss_rate"] == 0.5 and report["recall"] == 0.5
    assert {f["id"] for f in report["failures"]} == {"1", "2"} or {f["id"] for f in report["failures"]} == {"2"}
    assert report["verified"] == 0


def test_a_perfect_masker_scores_precision_one_and_no_misses():
    cases = exam.load()
    # an oracle that hides exactly the labelled PII strings and nothing else
    def oracle_text(case):
        text = case["text"]
        for s in case["pii"]:
            text = text.replace(s, "[X]")
        return text
    rows = [exam.score_case(c, oracle_text(c)) for c in cases]
    assert all(not r["misses"] and not r["destroyed"] for r in rows)


def test_the_committed_masker_leaks_and_damages_on_this_exam():
    """Regression on the finding itself: the only masker in the repo is a set of regexes. If someone fixes it, this test
    fails on purpose, and the gate row and docs/evaluation/eval-gate.md should be updated with the new numbers."""
    report = exam.run(exam.load(), exam.load_detector(exam.DEFAULT_DETECTOR))
    assert report["miss_rate"] > 0.2, "the masker leaks Arabic digits, bracketed and international phones, lowercase references"
    assert report["precision"] < 1.0, "it also masks 10-digit measurements as phone numbers"


def test_main_check_and_report(tmp_path, capsys):
    assert exam.main(["--check"]) == 0
    out = tmp_path / "pii.json"
    assert exam.main(["--out", str(out)]) == 0
    assert out.exists() and "precision" in capsys.readouterr().out


def test_an_invalid_exam_file_stops_the_run(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "x"}\n', encoding="utf-8")
    assert exam.main(["--data", str(path), "--check"]) == 1


@pytest.mark.parametrize("spec", ["tests.eval.master_pipeline:PIIMaskingGuardrail"])
def test_the_default_detector_loads(spec):
    mask = exam.load_detector(spec)
    assert "[EMAIL_REDACTED]" in mask("write to john.doe@nasa.gov")
