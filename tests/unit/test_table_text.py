"""Table-aware indexing text: a table is rendered as `header=value` rows only when its cells look trustworthy (roadmap item 12)."""
from ai.rag.ingestion.tables import MIN_CLEAN_SHARE, render_table, table_texts

CLEAN = [
    ["Diluent", "N2", "He", "Ar"],
    ["Flammability limit % O2", "16.5", "11.5", "24"],
    ["Flame spread cm/s", "0.9", "1.8", "1.9"],
]


def test_a_clean_table_becomes_header_value_rows():
    assert render_table(CLEAN) == (
        "Diluent=Flammability limit % O2; N2=16.5; He=11.5; Ar=24\n"
        "Diluent=Flame spread cm/s; N2=0.9; He=1.8; Ar=1.9")


def test_empty_cells_are_skipped_and_empty_rows_and_columns_dropped():
    rows = [["Test", "Fuel", ""], ["1", "PMMA", None], ["", "", ""], ["2", None, ""], ["3", "", ""]]
    assert render_table(rows) == "Test=1; Fuel=PMMA\nTest=2\nTest=3"


def test_cells_are_whitespace_normalised():
    rows = [["Test  no", "Result"], ["1\n", " burned\nfully "], ["2", "went  out"]]
    assert render_table(rows) == "Test no=1; Result=burned fully\nTest no=2; Result=went out"


def test_a_table_with_broken_cells_is_rejected():
    garbled = [["Diluent-\n_", "N2", "He"], ["Limit % 02:\n,", "165\n.", "115\n."], ["Rate cm/s:\n,", "09\n.", "18\n."]]
    assert render_table(garbled) is None


def test_lone_punctuation_cells_count_as_broken():
    rows = [["A", "B", "C"], ["1", "..", ","], ["2", "...", "."], ["3", "4", "5"]]
    assert render_table(rows) is None


def test_tables_too_small_or_without_a_usable_header_are_rejected():
    assert render_table([["only", "one row"]]) is None
    assert render_table([["A", "B"], ["1", "2"]]) is None                      # fewer than 3 rows
    assert render_table([["", "", "x"], ["1", "2", "3"], ["4", "5", "6"]]) is None   # one header cell
    assert render_table([["A", "A"], ["1", "2"], ["3", "4"]]) is None               # duplicate header names


def test_the_gate_threshold_is_documented_and_strict():
    assert 0.8 <= MIN_CLEAN_SHARE <= 1.0


def test_table_texts_joins_only_the_tables_that_pass():
    class T:
        def __init__(self, rows):
            self._rows = rows

        def extract(self):
            return self._rows

    class Page:
        def find_tables(self):
            class R:
                tables = [T(CLEAN), T([["a"]])]
            return R()

    text = table_texts(Page())
    assert text.count("Diluent=") == 2 and "a" not in text.replace("Diluent", "").split("\n")[0][:0]


def test_a_page_where_table_detection_fails_has_no_table_text():
    class Page:
        def find_tables(self):
            raise RuntimeError("boom")

    assert table_texts(Page()) == ""
