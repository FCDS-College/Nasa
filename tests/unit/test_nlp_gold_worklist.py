"""NLP gold annotation worklist (annotation-guidelines §4): selection rules, the validator and annotator agreement."""
import copy
import json
from collections import Counter

import pytest

from ai.rag.nlp import gold_worklist as gw

WORKLIST = gw.load_cases(gw.WORKLIST)
MANIFEST = json.loads(gw.MANIFEST.read_text(encoding="utf-8"))


def test_the_committed_worklist_is_what_the_pdfs_give_today():
    pytest.importorskip("fitz")
    worklist, manifest = gw.build()
    assert gw._dump_worklist(worklist) == gw.WORKLIST.read_text(encoding="utf-8")
    assert gw._dump_manifest(manifest) == gw.MANIFEST.read_text(encoding="utf-8")


def test_the_worklist_is_not_gold_and_the_gold_file_stays_empty():
    assert all(case["annotations"] == [] and case["annotator"] == "" for case in WORKLIST)
    assert gw.load_cases(gw.EVAL_DIR / "nlp_gold_v1.jsonl") == []


def test_selection_follows_the_guidelines():
    assert len(WORKLIST) == gw.TOTAL_CASES == len({c["gold_id"] for c in WORKLIST})
    per_document = Counter(c["document_id"] for c in WORKLIST)
    for document, n in per_document.items():
        available = MANIFEST["documents"][document]["eligible_pages"]
        assert n >= min(gw.PER_DOCUMENT, available) and n <= 3, document
    assert all(len(c["chunk_text"]) >= gw.MIN_CHARS for c in WORKLIST)
    splits_of = {}
    for case in WORKLIST:
        splits_of.setdefault(case["document_id"], set()).add(case["split"])
    assert all(len(s) == 1 for s in splits_of.values()), "a document in two splits leaks between them"
    counts = Counter(c["split"] for c in WORKLIST)
    for split, share in gw.SPLIT_SHARES.items():
        assert abs(counts[split] - share * len(WORKLIST)) <= 2, (split, counts)


def test_a_fifth_of_each_split_is_marked_for_double_annotation():
    double = Counter(MANIFEST["cases"][g]["split"] for g in MANIFEST["double_annotate"])
    counts = Counter(c["split"] for c in WORKLIST)
    assert sum(double.values()) == round(0.2 * len(WORKLIST))
    for split in gw.SPLIT_SHARES:
        assert double[split] == round(0.2 * counts[split])


def _filled(case, annotator="Ziad", spans=None):
    out = copy.deepcopy(case)
    out["annotator"] = annotator
    text = out["chunk_text"]
    word = next(m for m in gw._TOKEN.finditer(text) if len(m.group()) > 5)
    out["annotations"] = spans if spans is not None else [
        {"record_type": "phenomenon", "char_start": word.start(), "char_end": word.end(), "text": word.group()}]
    return out


def test_a_correctly_filled_case_validates():
    problems, _ = gw.validate([_filled(WORKLIST[0])], MANIFEST)
    assert problems == []


@pytest.mark.parametrize("break_it,message", [
    (lambda c: c["annotations"][0].update(text="something else"), "is not chunk_text"),
    (lambda c: c["annotations"][0].update(record_type="platform"), "not one of the 14 labels"),
    (lambda c: c["annotations"][0].update(char_end=10**6), "outside the chunk"),
    (lambda c: c.update(annotator="Claude"), "looks like an AI"),
    (lambda c: c.update(chunk_text=c["chunk_text"] + " "), "differs from the worklist"),
    (lambda c: c.update(split="holdout" if c["split"] != "holdout" else "dev"), "the worklist says"),
    (lambda c: c.update(gold_id="NG-999"), "not in the worklist"),
])
def test_the_validator_rejects_a_case_that_cannot_be_gold(break_it, message):
    case = _filled(WORKLIST[0])
    break_it(case)
    problems, _ = gw.validate([case], MANIFEST)
    assert any(message in p for p in problems), problems


def test_the_unfilled_worklist_passes_partial_validation():
    problems, _ = gw.validate(copy.deepcopy(WORKLIST), MANIFEST, require_annotated=False)
    assert problems == []


def test_a_partial_file_is_allowed_with_partial_but_reports_what_is_missing():
    problems, warnings = gw.validate([_filled(WORKLIST[0])], MANIFEST, require_annotated=False)
    assert problems == []
    problems, warnings = gw.validate([copy.deepcopy(WORKLIST[1])], MANIFEST)
    assert any("no annotator" in p for p in problems)
    assert any("not in this file yet" in w for w in warnings)


def test_annotations_copied_from_the_pipeline_are_flagged():
    case = WORKLIST[0]
    spans = sorted(gw._pipeline_spans(case))
    if not spans:
        pytest.skip("the extractors find nothing on this page")
    copied = _filled(case, spans=[{"record_type": t, "char_start": s, "char_end": e, "text": case["chunk_text"][s:e]}
                                  for t, s, e in spans])
    _, warnings = gw.validate([copied], MANIFEST)
    assert any("exactly what the extractors emit" in w for w in warnings)


def test_agreement_is_cohen_kappa_over_tokens_and_needs_two_annotators():
    case = WORKLIST[0]
    a, b = _filled(case, "Ziad"), _filled(case, "Eman")
    assert gw.agreement([a], [b])["kappa"] == pytest.approx(1.0)
    b_other = _filled(case, "Eman", spans=[])
    result = gw.agreement([a], [b_other])
    assert result["kappa"] < gw.KAPPA_THRESHOLD and not result["passes"]
    with pytest.raises(ValueError, match="two different annotators"):
        gw.agreement([a], [_filled(case, "ziad")])


def test_cohen_kappa_matches_a_hand_computed_value():
    # 10 tokens, each annotator 6 x O and 4 x fuel: observed agreement 0.8, expected 0.6*0.6 + 0.4*0.4 = 0.52,
    # kappa = (0.8 - 0.52) / (1 - 0.52)
    a = ["O"] * 6 + ["fuel"] * 4
    b = ["O"] * 5 + ["fuel"] + ["fuel"] * 3 + ["O"]
    assert gw.cohen_kappa(a, b) == pytest.approx(0.28 / 0.48)
