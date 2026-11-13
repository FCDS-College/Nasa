"""Query-aware evidence windows: the model should read the part of a page that answers the question (audit finding G-1)."""
from ai.rag.retrieval.evidence_window import WINDOW_CHARS, best_window, question_terms

FILLER = "The apparatus description continues with unrelated mounting details and calibration remarks. "


def _page(answer_sentence, *, before=1500, after=1500):
    return (FILLER * (before // len(FILLER) + 1))[:before] + " " + answer_sentence + " " + (FILLER * (after // len(FILLER) + 1))[:after]


def test_the_window_contains_the_sentence_that_answers_the_question():
    answer = "Extinction of PMMA occurred at an oxygen concentration of 14 percent."
    text = _page(answer)
    window = best_window(text, "At what oxygen concentration did PMMA extinction occur?")
    assert answer in window
    assert text.index(answer) > 400, "the answer must sit beyond the old 400-character prefix for this test to mean anything"


def test_the_window_is_bounded_and_never_cuts_a_word():
    text = _page("The rare term zirconia appears only here.")
    window = best_window(text, "zirconia")
    assert 0 < len(window) <= WINDOW_CHARS
    assert text.count(window) == 1
    start = text.index(window)
    assert start == 0 or text[start - 1].isspace()
    assert start + len(window) == len(text) or text[start + len(window)].isspace()


def test_a_rarer_term_outweighs_a_common_one():
    common = "Flame spread was observed and the flame front was recorded. " * 40
    rare = "A PMMA sample was used."
    text = common + rare + " " + common
    assert "PMMA" in best_window(text, "PMMA flame")


def test_with_no_matching_term_the_page_prefix_is_returned():
    text = _page("Nothing relevant here.")
    assert best_window(text, "zeppelin") == text[:len(best_window(text, "zeppelin"))]
    assert best_window(text, "zeppelin").startswith("The apparatus")


def test_short_text_is_returned_whole():
    assert best_window("A short page about flames.", "flames") == "A short page about flames."


def test_ligatures_and_case_do_not_hide_a_match():
    text = _page("The ﬂame speed was 3.2 cm/s in microgravity.")      # 'ﬂame' with a ligature, as PDFs often store it
    assert "3.2 cm/s" in best_window(text, "What was the FLAME speed?")


def test_numeric_and_chemical_tokens_are_kept():
    terms = question_terms("Does O2 change extinction at 0.1 atm in He diluent?")
    assert {"o2", "0.1", "atm", "he", "extinction", "diluent"} <= terms
    assert "does" not in terms and "in" not in terms
