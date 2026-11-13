"""Window-level indexing: split a page into windows the embedder can read in full, then aggregate window hits to pages."""
import random

import pytest

from ai.rag.ingestion.windows import MAX_WINDOW_CHARS, split_windows
from ai.rag.retrieval.aggregate import aggregate_windows

SENTENCE = "The flame front moved slowly across the PMMA sample under reduced pressure. "


def _page(sentences):
    return "".join(f"{SENTENCE[:-2]} {i}. " for i in range(sentences)).strip()


def test_a_short_page_is_one_window():
    windows = split_windows("A short page.")
    assert [(w.ordinal, w.start, w.end, w.text) for w in windows] == [(0, 0, 13, "A short page.")]


def test_an_empty_page_has_no_windows():
    assert split_windows("") == [] and split_windows("   \n ") == []


def test_every_character_of_a_long_page_is_in_some_window_and_offsets_are_exact():
    text = _page(120)
    windows = split_windows(text, size=1200, overlap=200)
    assert len(windows) > 3
    covered = [False] * len(text)
    for window in windows:
        assert text[window.start:window.end] == window.text and len(window.text) <= 1200
        for i in range(window.start, window.end):
            covered[i] = True
    assert all(covered[i] or text[i].isspace() for i in range(len(text)))


def test_consecutive_windows_overlap_and_make_progress():
    text = _page(120)
    windows = split_windows(text, size=1200, overlap=200)
    for before, after in zip(windows, windows[1:]):
        assert after.start > before.start and after.end > before.end
        assert 0 < before.end - after.start <= 400


def test_windows_break_at_sentence_ends_when_there_is_one():
    text = _page(60)
    for window in split_windows(text, size=1200, overlap=200)[:-1]:
        assert window.text.rstrip().endswith(".")


def test_text_without_any_break_still_terminates_and_stays_within_the_limit():
    text = "x" * 5000
    windows = split_windows(text, size=1200, overlap=200)
    assert windows[-1].end == 5000 and all(len(w.text) <= 1200 for w in windows)


def test_the_size_cannot_exceed_what_the_embedder_reads():
    with pytest.raises(ValueError):
        split_windows("text", size=MAX_WINDOW_CHARS + 1)
    with pytest.raises(ValueError):
        split_windows("text", size=100, overlap=100)


def test_splitting_is_deterministic():
    rng = random.Random(1)
    text = " ".join(rng.choice(["flame", "pressure.", "oxygen", "He", "0.1", "atm;"]) for _ in range(900))
    assert split_windows(text) == split_windows(text)


def test_window_hits_aggregate_to_the_best_window_per_page():
    hits = [("c1", 0.60), ("c2", 0.71), ("c1", 0.80), ("c3", 0.55), ("c2", 0.70)]
    assert aggregate_windows(hits) == [("c1", 0.80), ("c2", 0.71), ("c3", 0.55)]


def test_aggregation_breaks_ties_by_page_id_and_applies_the_limit():
    assert aggregate_windows([("b", 0.7), ("a", 0.7), ("c", 0.6)], limit=2) == [("a", 0.7), ("b", 0.7)]
    assert aggregate_windows([]) == []
