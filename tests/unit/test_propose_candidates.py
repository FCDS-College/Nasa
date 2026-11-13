"""The annotator worklist proposes passages to write questions about; it never produces gold."""
import pytest

from ai.rag.evaluation.propose_candidates import candidate_passages, sentence_spans

PAGE = ("The apparatus is described in Section 2. Flame speed was 3.2 cm/s at 0.1 atm in microgravity. "
        "Results are discussed below. The ignition delay increased to 45 ms when oxygen fell to 18 %.\n"
        "Acknowledgements are on the last page.")


def test_sentence_spans_reconstruct_the_page_text():
    spans = sentence_spans(PAGE)
    assert spans and all(PAGE[s:e].strip() == PAGE[s:e] and PAGE[s:e] for s, e in spans)
    assert PAGE[spans[1][0]:spans[1][1]].startswith("Flame speed was 3.2 cm/s")
    for (_, previous_end), (start, _) in zip(spans, spans[1:]):
        assert start >= previous_end, "sentences must not overlap"


def test_only_sentences_with_a_measurement_are_proposed():
    rows = candidate_passages(PAGE)
    assert [r["text"][:20] for r in rows] == ["Flame speed was 3.2 ", "The ignition delay i"]
    assert all(PAGE[r["char_start"]:r["char_end"]] == r["text"] for r in rows)
    assert rows[0]["measurements"] == ["3.2 cm/s", "0.1 atm"]


def test_a_page_without_measurements_proposes_nothing():
    assert candidate_passages("The apparatus is described in Section 2. Results are discussed below.") == []


def test_proposals_are_marked_as_not_gold():
    assert all(r["status"] == "proposal" for r in candidate_passages(PAGE))


def test_reading_pdfs_needs_pymupdf_and_says_so(monkeypatch, tmp_path):
    import builtins

    from ai.rag.evaluation import propose_candidates

    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("no fitz")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)
    with pytest.raises(SystemExit, match="PyMuPDF"):
        list(propose_candidates.propose(tmp_path))


# --- the text annotators must work from ---------------------------------------------------------------------------------

def test_indexed_pages_give_the_verbatim_and_the_indexed_text_of_each_page(tmp_path):
    import fitz

    from ai.rag.evaluation.propose_candidates import indexed_pages

    pdf = fitz.open()
    for number in range(1, 5):
        page = pdf.new_page()
        page.insert_text((72, 72), "American Institute of Aeronautics and Astronautics", fontsize=9)
        page.insert_text((72, 120), f"Flame spread was measured on page {number} at 0.1 atm.", fontsize=11)
        page.insert_text((72, 760), str(number), fontsize=9)
    path = tmp_path / "paper.pdf"
    pdf.save(path)

    pages = indexed_pages(path)

    assert [p["page"] for p in pages] == [1, 2, 3, 4]
    assert all("American Institute" in p["verbatim"] for p in pages)                       # what the evidence excerpt holds
    assert "American Institute" in pages[0]["indexed"] and "American Institute" not in pages[1]["indexed"]   # what is indexed
    assert pages[1]["verbatim"].endswith("2") and not pages[1]["indexed"].endswith("2")
