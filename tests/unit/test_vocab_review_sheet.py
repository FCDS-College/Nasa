"""Review sheet for the D1 seed vocabularies: what each entry matches in a corpus, with context, for a domain expert to judge."""
import csv
import io

from ai.rag.nlp.review_sheet import COLUMNS, review_rows, write_csv

VOCAB = {"material": {"polymethyl methacrylate": ["PMMA", "acrylic"], "cellulose": []},
         "oxidizer": {"oxygen": [{"text": "O2", "case_sensitive": True}]}}
PAGES = [
    {"doc": "D1", "page": 1, "text": "Samples of PMMA and acrylic were burned in O2. The acrylic sheet was 2 mm thick."},
    {"doc": "D2", "page": 4, "text": "Pure oxygen was used; the O2 flow was steady."},
]


def _row(rows, canonical):
    return next(r for r in rows if r["canonical"] == canonical)


def test_each_entry_counts_hits_documents_and_surface_forms():
    row = _row(review_rows(VOCAB, PAGES), "polymethyl methacrylate")
    assert row["type"] == "material" and row["hits"] == 3 and row["documents"] == 1
    assert row["surface_forms"] == "acrylic x2; PMMA x1"


def test_case_sensitive_aliases_and_the_canonical_name_are_counted_separately():
    row = _row(review_rows(VOCAB, PAGES), "oxygen")
    assert row["hits"] == 3 and row["documents"] == 2 and row["surface_forms"] == "O2 x2; oxygen x1"


def test_an_entry_with_no_hits_is_flagged_not_dropped():
    row = _row(review_rows(VOCAB, PAGES), "cellulose")
    assert row["hits"] == 0 and row["flag"] == "no hits in this corpus" and row["contexts"] == ""


def test_contexts_show_the_match_in_brackets_with_its_document_and_page():
    row = _row(review_rows(VOCAB, PAGES, contexts=1), "polymethyl methacrylate")
    assert row["contexts"].startswith("D1 p1: ") and "[PMMA]" in row["contexts"] and "\n" not in row["contexts"]


def test_reviewer_columns_are_present_and_empty_and_the_csv_round_trips():
    rows = review_rows(VOCAB, PAGES)
    out = io.StringIO()
    write_csv(rows, out)
    read = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert list(read[0].keys()) == COLUMNS and len(read) == 3
    assert all(r["decision"] == "" and r["correction"] == "" and r["notes"] == "" for r in read)
