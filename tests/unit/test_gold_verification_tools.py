"""Tools that help a person verify AI-drafted passage gold cases, and adopt only the ones they accept."""
import csv
import io
import json

import pytest

from ai.rag.evaluation.adopt_drafts import adopt
from ai.rag.evaluation.passage_gold import PassageCase, load_passage_gold, validate, verified_cases
from ai.rag.evaluation.verification_sheet import COLUMNS, competing_pages, sheet_rows, write_csv

PAGES = {
    ("D1", 1): "The upward burn test requires the flame to travel less than 15 cm before the sample goes out.",
    ("D1", 2): "Shipping logistics and procurement schedules are described in the appendix.",
    ("D2", 5): "A flame burned upward over the sample for 15 cm in the older test method before going out.",
}


def _case(gold_id, question, *, answerable=True, doc="D1", page=1, text=None, split="dev", kind=None):
    evidence = []
    if answerable:
        body = PAGES[(doc, page)]
        text = text or body[:40]
        evidence = [{"document_id": doc, "page": page, "char_start": body.index(text), "char_end": body.index(text) + len(text), "text": text}]
    return PassageCase.from_dict({"gold_id": gold_id, "split": split, "question": question, "answerable": answerable, "evidence": evidence,
                                  "question_type": "other", "unanswerable_kind": kind, "author": "claude (AI draft)",
                                  "verified_by": [], "status": "draft"})


def test_competing_pages_are_other_pages_that_share_the_questions_distinctive_terms():
    case = _case("PG-001", "How far may a flame travel upward before the sample goes out?")
    found = competing_pages(case, PAGES, limit=2)
    assert [(d, p) for d, p, _ in found][0] == ("D2", 5)                    # the other page about upward flame travel
    assert ("D1", 1) not in [(d, p) for d, p, _ in found]                   # never the evidence page itself


def test_same_figures_on_lists_other_pages_that_repeat_a_figure_of_the_evidence():
    from ai.rag.evaluation.verification_sheet import same_figures_on

    pages = {**PAGES, ("D3", 1): "The sample must not burn farther than 15 cm in the standard check."}
    case = _case("PG-001", "How far may a flame travel upward before the sample goes out?", text="less than 15 cm before the sample goes out.")
    assert [(d, p) for d, p, _ in same_figures_on(case, pages)] == [("D2", 5), ("D3", 1)]
    assert same_figures_on(_case("PG-009", "What is a good recipe for a chocolate cake?", answerable=False, kind="out_of_domain"), pages) == []


def test_sheet_rows_have_empty_reviewer_columns_and_unanswerable_rows_list_pages_that_might_answer_them():
    cases = [_case("PG-001", "How far may a flame travel upward before the sample goes out?"),
             _case("PG-002", "How far does a flame travel upward in a test of aerogel?", answerable=False, kind="in_domain_not_in_corpus")]
    rows = sheet_rows(cases, PAGES)
    assert rows[0]["evidence"].startswith("D1 p1:") and rows[1]["evidence"] == ""
    assert rows[1]["competing_pages"] and all(r[c] == "" for r in rows for c in ("answers_question", "unique", "question_clear", "notes"))
    out = io.StringIO()
    write_csv(rows, out)
    assert list(next(csv.DictReader(io.StringIO(out.getvalue()))).keys()) == COLUMNS


def test_adopting_accepted_cases_marks_them_verified_by_the_named_person(tmp_path):
    drafts = tmp_path / "drafts.jsonl"
    target = tmp_path / "gold.jsonl"
    cases = [_case("PG-001", "How far may a flame travel upward before the sample goes out?"),
             _case("PG-002", "What is a good recipe for a chocolate cake?", answerable=False, kind="out_of_domain")]
    drafts.write_text("\n".join(json.dumps(_raw(c)) for c in cases) + "\n", encoding="utf-8")
    summary = adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-001", "PG-002"], page_texts=PAGES, min_unanswerable_share=0.25)
    loaded = load_passage_gold(target)
    assert summary["adopted"] == ["PG-001", "PG-002"] and len(verified_cases(loaded)) == 2
    assert all(c.verified_by == ("Dr Reviewer",) and c.status == "verified" for c in loaded)
    assert validate(loaded, page_texts=PAGES) == []


def test_adoption_refuses_the_author_an_ai_name_an_unknown_id_and_a_set_that_breaks_the_rules(tmp_path):
    drafts, target = tmp_path / "d.jsonl", tmp_path / "g.jsonl"
    cases = [_case("PG-001", "How far may a flame travel upward before the sample goes out?")]
    drafts.write_text(json.dumps(_raw(cases[0])) + "\n", encoding="utf-8")
    human = tmp_path / "human.jsonl"
    human.write_text(json.dumps({**_raw(cases[0]), "author": "Dr Writer"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="author"):
        adopt(human, target, verifier="dr writer", accept=["PG-001"], page_texts=PAGES)
    with pytest.raises(ValueError, match="AI"):
        adopt(drafts, target, verifier="Claude", accept=["PG-001"], page_texts=PAGES)
    with pytest.raises(ValueError, match="PG-009"):
        adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-009"], page_texts=PAGES)
    with pytest.raises(ValueError, match="unanswerable"):          # only answerable accepted: the 25 % rule is not met
        adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-001"], page_texts=PAGES)
    assert not target.exists()                                      # nothing is written on a refusal


def test_adopting_twice_does_not_duplicate_and_keeps_earlier_adoptions(tmp_path):
    drafts, target = tmp_path / "d.jsonl", tmp_path / "g.jsonl"
    cases = [_case("PG-001", "How far may a flame travel upward before the sample goes out?"),
             _case("PG-002", "What is a good recipe for a chocolate cake?", answerable=False, kind="out_of_domain")]
    drafts.write_text("\n".join(json.dumps(_raw(c)) for c in cases) + "\n", encoding="utf-8")
    adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-001", "PG-002"], page_texts=PAGES)
    again = adopt(drafts, target, verifier="Dr Other", accept=["PG-001"], page_texts=PAGES)
    loaded = load_passage_gold(target)
    assert again["adopted"] == [] and again["already_adopted"] == ["PG-001"] and len(loaded) == 2
    assert next(c for c in loaded if c.gold_id == "PG-001").verified_by == ("Dr Reviewer",)


def _raw(case):
    return {"gold_id": case.gold_id, "split": case.split, "question": case.question, "answerable": case.answerable,
            "evidence": [{"document_id": e.document_id, "page": e.page, "char_start": e.char_start, "char_end": e.char_end, "text": e.text}
                         for e in case.evidence],
            "question_type": case.question_type, "unanswerable_kind": case.unanswerable_kind, "author": case.author,
            "verified_by": list(case.verified_by), "status": case.status}


# --- staged adoption and person-written unanswerable questions --------------------------------------------------------------

def test_a_partial_set_is_refused_unless_the_caller_says_it_is_incomplete(tmp_path):
    drafts, target = tmp_path / "d.jsonl", tmp_path / "g.jsonl"
    drafts.write_text(json.dumps(_raw(_case("PG-001", "How far may a flame travel upward before the sample goes out?"))) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unanswerable"):
        adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-001"], page_texts=PAGES)
    summary = adopt(drafts, target, verifier="Dr Reviewer", accept=["PG-001"], page_texts=PAGES, allow_incomplete=True)
    assert summary["adopted"] == ["PG-001"] and summary["complete"] is False and target.exists()


def test_a_second_person_completes_the_set_under_their_own_name(tmp_path):
    drafts, target = tmp_path / "d.jsonl", tmp_path / "g.jsonl"
    human = {**_raw(_case("PG-002", "What is a good recipe for a chocolate cake?", answerable=False, kind="out_of_domain")), "author": "Anas"}
    drafts.write_text(json.dumps(_raw(_case("PG-001", "How far may a flame travel upward before the sample goes out?"))) + "\n" + json.dumps(human) + "\n",
                      encoding="utf-8")
    adopt(drafts, target, verifier="Anas", accept=["PG-001"], page_texts=PAGES, allow_incomplete=True)
    with pytest.raises(ValueError, match="author"):
        adopt(drafts, target, verifier="Anas", accept=["PG-002"], page_texts=PAGES)           # the author cannot verify their own question
    done = adopt(drafts, target, verifier="Ziad", accept=["PG-002"], page_texts=PAGES, min_unanswerable_share=0.25)
    loaded = {c.gold_id: c for c in load_passage_gold(target)}
    assert done["complete"] is True and loaded["PG-001"].verified_by == ("Anas",) and loaded["PG-002"].verified_by == ("Ziad",)


def test_add_unanswerable_appends_drafts_with_the_authors_name_and_continues_the_numbering(tmp_path):
    from ai.rag.evaluation.add_unanswerable import add_unanswerable

    drafts = tmp_path / "d.jsonl"
    drafts.write_text(json.dumps(_raw(_case("PG-001", "How far may a flame travel upward before the sample goes out?"))) + "\n", encoding="utf-8")
    added = add_unanswerable(drafts, author="Anas", questions=["What heat flux ignites a lithium cell in orbit?", "How do I renew a passport in Egypt?"],
                             kind_of={"How do I renew a passport in Egypt?": "out_of_domain"})
    cases = {c.gold_id: c for c in load_passage_gold(drafts)}
    assert added == ["PG-002", "PG-003"]
    assert cases["PG-002"].author == "Anas" and cases["PG-002"].status == "draft" and cases["PG-002"].verified_by == ()
    assert cases["PG-002"].unanswerable_kind == "in_domain_not_in_corpus" and cases["PG-003"].unanswerable_kind == "out_of_domain"
    assert cases["PG-002"].evidence == () and not cases["PG-002"].answerable
    assert [cases[i].split for i in ("PG-002", "PG-003")] == ["dev", "validation"]


def test_add_unanswerable_refuses_duplicates_short_questions_and_an_ai_author(tmp_path):
    from ai.rag.evaluation.add_unanswerable import add_unanswerable

    drafts = tmp_path / "d.jsonl"
    drafts.write_text(json.dumps(_raw(_case("PG-001", "How far may a flame travel upward before the sample goes out?"))) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        add_unanswerable(drafts, author="Anas", questions=["How far may a flame travel upward before the sample goes out?"])
    with pytest.raises(ValueError, match="short"):
        add_unanswerable(drafts, author="Anas", questions=["Why?"])
    with pytest.raises(ValueError, match="AI"):
        add_unanswerable(drafts, author="Claude", questions=["What heat flux ignites a lithium cell in orbit?"])
    assert len(load_passage_gold(drafts)) == 1                                   # nothing was written on a refusal


def test_the_absence_report_counts_pages_per_distinctive_term_and_lists_the_closest_pages():
    from ai.rag.evaluation.add_unanswerable import absence_report

    pages = {("D1", 1): "The flame spread over the sample at reduced pressure.", ("D2", 3): "Heat flux ignited the sample in the chamber."}
    report = absence_report("What heat flux ignites a lithium cell in orbit?", pages)
    assert report["term_pages"]["lithium"] == 0 and report["term_pages"]["flux"] == 1 and report["term_pages"]["heat"] == 1
    assert report["absent_terms"] == ["cell", "ignites", "lithium", "orbit"]
    assert report["closest_pages"][0][:2] == ("D2", 3)
