"""Page-text normalisation before indexing (audit finding R-3).

Measured on the committed NTRS PDFs: 504 ligature characters (`ﬂame` is a different PostgreSQL lexeme from `flame`),
470 words split by a hyphen at a line break, running headers on dozens of pages, and 23% of pages with words stacked one
per line. None of this may change what a citation says: only the text that is indexed is normalised.
"""
from ai.rag.ingestion.normalize import (
    NORMALIZER_VERSION, dehyphenate, fold_ligatures, normalize_document, strip_running_lines, unstack_lines,
)


def test_ligatures_are_folded_to_plain_letters():
    assert fold_ligatures("The ﬂame and ﬁre of an eﬃcient ﬀect") == "The flame and fire of an efficient ffect"


def test_text_without_ligatures_is_untouched():
    text = "Flame spread at 0.1 atm: 3.2 cm/s (µm, 21 %)."
    assert fold_ligatures(text) == text


# --- hyphenation at a line break ------------------------------------------------------------------------------------

def test_a_word_split_at_a_line_break_is_rejoined_when_the_document_uses_it_whole():
    pages = ["Lean flam-\nmability limits were measured.", "The flammability of PMMA was lower in microgravity."]
    assert dehyphenate(pages)[0] == "Lean flammability limits were measured."


def test_a_real_compound_split_at_a_line_break_keeps_its_hyphen():
    out = dehyphenate(["The opposed-\nflow velocity was varied.", "No other mention of the compound."])
    assert out[0] == "The opposed-flow velocity was varied."


def test_hyphens_inside_a_line_and_before_digits_are_not_touched():
    text = "A well-known 5-\n10 mm range and a mid-line high-speed camera."
    assert dehyphenate([text, "x"])[0] == text.replace("5-\n10", "5-\n10")


# --- words stacked one per line -------------------------------------------------------------------------------------

STACKED = "\n".join("fire resistance is determined within a closed chamber at the worst-case-use oxygen concentration "
                    "and pressure environment currently seen in space materials testing programs today".split())


def test_stacked_words_are_joined_into_a_paragraph_and_blank_lines_survive():
    page = STACKED + "\n\n" + STACKED
    out = unstack_lines(page)
    assert out.count("\n\n") == 1 and "fire resistance is determined" in out and "\n" not in out.replace("\n\n", "")


def test_a_column_of_numbers_is_not_a_stacked_paragraph():
    table = "\n".join(str(n) for n in range(30))
    assert unstack_lines(table) == table


def test_ordinary_prose_and_short_pages_are_untouched():
    prose = "Flame spread rates were measured in microgravity.\nThe fuel was PMMA sheet.\n" * 12
    assert unstack_lines(prose) == prose
    short = "a\nb\nc"
    assert unstack_lines(short) == short


# --- running headers and page numbers -------------------------------------------------------------------------------

def _pages(n, header="American Institute of Aeronautics and Astronautics"):
    return [f"{header}\nBody text of page {i} about flames and fuel.\nMore body text {i}.\n{i}" for i in range(1, n + 1)]


def test_a_repeated_header_is_kept_on_its_first_page_only_and_page_numbers_are_removed():
    # Kept once because a header can carry the document's topic ("Sub Topic: Fire Research": stripping it everywhere removed the
    # only 'fire' mention on 8 pages of a paper), while its repeats are noise on every other page.
    out = strip_running_lines(_pages(6))
    assert "American Institute" in out[0] and all("American Institute" not in page for page in out[1:])
    assert all(page.splitlines()[-1].startswith("More body text") for page in out)


def test_the_same_words_in_the_middle_of_a_page_are_kept():
    pages = _pages(6)
    pages[2] = "Intro line.\nAs the American Institute of Aeronautics and Astronautics noted,\nbody.\nend"
    pages[2] += "\nAmerican Institute of Aeronautics and Astronautics"       # this one is in the last position: removed
    out = strip_running_lines(pages)
    assert "As the American Institute" in out[2]


def test_a_short_document_is_not_stripped():
    pages = _pages(2)
    assert strip_running_lines(pages) == pages


# --- the whole pipeline ---------------------------------------------------------------------------------------------

def test_normalize_document_applies_every_step_and_is_idempotent():
    pages = _pages(6)
    pages[0] = pages[0].replace("flames", "ﬂames").replace("body", "flam-\nmability")
    pages[1] = pages[1].replace("flames and fuel", "flammability and fuel")
    once = normalize_document(pages)
    assert "flames" in once[0] and "flammability" in once[0] and "ﬂ" not in once[0] and "American Institute" not in once[1]
    assert normalize_document(once) == once


def test_a_page_that_would_become_empty_keeps_its_text():
    pages = ["Header line\n1", "Header line\n2", "Header line\n3", "Header line\n4"]
    assert all(page.strip() for page in normalize_document(pages))


def test_the_version_is_recorded():
    assert NORMALIZER_VERSION.startswith("text-normalize-")
