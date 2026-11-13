"""Query-aware evidence windows.

Retrieval ranks a whole page; the model should read the part of the page that answers the question, not its first
few hundred characters (audit finding G-1: for about half of the gold questions the best passage began after
character 400). The best window is chosen lexically, which is cheap and needs no model: windows are scored by how
many of the question's distinctive terms they contain, rarer terms (within the page) counting more.

Pure Python, no storage or model imports.
"""
from __future__ import annotations

import math
import re
import unicodedata

# Words that say nothing about what a question is about. (`flame_api.main` shares this set.)
STOPWORDS = frozenset(
    "a an and are as at be been by can could did do does for from has have how in into is it its of on or "
    "that the their there these this to was were what when where which who why will with would about "
    "between during after before than then them they you your tell explain describe give show find".split()
)
WINDOW_CHARS = 1200
_STEP = 300
_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def _normalise(text: str) -> str:
    """NFKC folds ligatures (`ﬂ` -> `fl`) and compatibility forms; lower-case. For matching only: never for output."""
    return unicodedata.normalize("NFKC", text).lower()


def question_terms(question: str) -> set[str]:
    """Distinctive terms of a question. Two-character tokens such as `o2` and `he` are kept: they are chemistry."""
    return {t for t in _TOKEN.findall(_normalise(question)) if t not in STOPWORDS and len(t) >= 2}


def _window_tokens(window: str) -> set[str]:
    tokens = set(_TOKEN.findall(_normalise(window)))
    for token in list(tokens):
        if "-" in token:                       # `oxygen-enriched` also answers a question about `oxygen`
            tokens.update(part for part in token.split("-") if len(part) >= 2)
    return tokens


def _windows(text: str, size: int, step: int) -> list[str]:
    """Overlapping windows that start and end on whitespace (a token longer than `size` is cut)."""
    starts = list(range(0, len(text), step))
    last = max(0, len(text) - size)
    if last not in starts:
        starts.append(last)
    windows: list[str] = []
    for start in starts:
        if start > 0 and not text[start - 1].isspace():
            while start < len(text) and not text[start].isspace():
                start += 1
        end = min(start + size, len(text))
        if end < len(text):
            cut = end
            while cut > start and not text[cut].isspace():
                cut -= 1
            end = cut if cut > start else end
        window = text[start:end].strip()
        if window and window not in windows:
            windows.append(window)
    return windows


def best_window(text: str, question: str, *, size: int = WINDOW_CHARS) -> str:
    """The window of `text` (at most `size` characters) that best matches `question`.

    Falls back to the start of the page when no term of the question occurs in it, which is what the chat
    path used before and is the right default for a page retrieved on meaning alone.
    """
    if len(text) <= size:
        return text.strip()
    windows = _windows(text, size, _STEP)
    terms = question_terms(question)
    if not terms:
        return windows[0]
    tokens = [_window_tokens(w) for w in windows]
    document_frequency = {t: sum(t in found for found in tokens) for t in terms}
    weights = {t: math.log(1 + len(windows) / df) for t, df in document_frequency.items() if df}
    scores = [sum(weights.get(t, 0.0) for t in terms & found) for found in tokens]
    best = max(scores)
    return windows[0] if best == 0 else windows[scores.index(best)]
