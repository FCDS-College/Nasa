"""Page-text normalisation before indexing (audit finding R-3). Pure Python.

PDF text comes out of the extractor with artefacts that lexical and dense retrieval both stumble on. Measured on the committed
NTRS papers (PyMuPDF text): 504 ligature characters (`ﬂame`, which PostgreSQL stores as a different lexeme from `flame`: a plain
"flame" query misses 18 pages whose only occurrence is the ligature form), 470 words split by a hyphen at a line break (a
`flam-\\nmability` does not match "flammability"), running headers repeated on dozens of pages, and 23% of pages with words stacked
one per line.

Only the text that is INDEXED is normalised. The evidence excerpt a citation points at stays exactly as extracted
(`extraction_method = "verbatim_text"` is part of the API contract).

Order matters: boilerplate and hyphen splits are handled while the text still has its lines; stacked words are joined last.
"""
from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from collections.abc import Sequence

NORMALIZER_VERSION = "text-normalize-1.0.0"

_LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})
_SPLIT_WORD = re.compile(r"([A-Za-z]+)-\n([a-z]+)")
_PAGE_NUMBER = re.compile(r"^(?:\d{1,4}|[ivxlc]{1,6})$", re.IGNORECASE)
_MIN_STACKED_LINES = 20
_STACKED_MEDIAN_CHARS = 12
_EDGE_LINES = 2            # the first and last lines of a page are where headers, footers and page numbers live
_RUNNING_MIN_PAGES = 3     # a line must repeat on at least this many pages (and on 30% of them) to be a running line
_RUNNING_MAX_CHARS = 100


def fold_ligatures(text: str) -> str:
    """`ﬂ` -> `fl`, `ﬁ` -> `fi`, ... A targeted map, not NFKC: NFKC would also rewrite `µ`, superscripts and fractions."""
    return text.translate(_LIGATURES)


def dehyphenate(pages: Sequence[str]) -> list[str]:
    """Rejoin words split by a hyphen at a line break, when the document itself uses the joined word.

    `flam-\\nmability` becomes `flammability` if `flammability` occurs elsewhere in the document; otherwise the hyphen stays and
    only the line break goes (`opposed-\\nflow` -> `opposed-flow`), because a real compound must not be glued together.
    """
    without_splits = _SPLIT_WORD.sub(" ", "\n".join(pages))      # a split word must not vouch for itself
    vocabulary = {word.lower() for word in re.findall(r"[A-Za-z]{4,}", without_splits)}

    def join(match: re.Match) -> str:
        left, right = match.group(1), match.group(2)
        return left + right if (left + right).lower() in vocabulary else f"{left}-{right}"

    return [_SPLIT_WORD.sub(join, page) for page in pages]


def unstack_lines(text: str) -> str:
    """Join pages whose words are stacked one per line into paragraphs (blank lines stay as paragraph breaks).

    Needs many lines, a short median, mostly single tokens and mostly words: a column of numbers is not a paragraph.
    """
    lines = text.split("\n")
    content = [line.strip() for line in lines if line.strip()]
    if len(content) < _MIN_STACKED_LINES:
        return text
    single_token = sum(" " not in line for line in content) / len(content)
    wordy = sum(bool(re.search(r"[A-Za-z]{2,}", line)) for line in content) / len(content)
    if statistics.median(len(line) for line in content) >= _STACKED_MEDIAN_CHARS or single_token < 0.7 or wordy < 0.6:
        return text
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def _key(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip()).lower()


def _edge_indexes(lines: list[str]) -> list[int]:
    filled = [i for i, line in enumerate(lines) if line.strip()]
    return sorted(set(filled[:_EDGE_LINES] + filled[-_EDGE_LINES:]))


def strip_running_lines(pages: Sequence[str]) -> list[str]:
    """Remove page numbers and the lines a document repeats at the top or bottom of its pages (running headers and footers).

    Only the first and last two lines of a page are considered, so the same words in the middle of a page are kept. A running
    line is kept on the first page where it appears and removed from the repeats: a header can carry the document's topic
    ("Sub Topic: Fire Research"; stripping it everywhere removed the only 'fire' mention on 8 pages of one paper), while its
    repeats are noise on every other page. A document of fewer than three pages is returned unchanged.
    """
    if len(pages) < _RUNNING_MIN_PAGES:
        return list(pages)
    counts: Counter[str] = Counter()
    for page in pages:
        lines = page.split("\n")
        counts.update({_key(lines[i]) for i in _edge_indexes(lines)})
    threshold = max(_RUNNING_MIN_PAGES, math.ceil(0.3 * len(pages)))
    running = {key for key, count in counts.items() if count >= threshold and 0 < len(key) <= _RUNNING_MAX_CHARS}
    out = []
    kept_once: set[str] = set()
    for page in pages:
        lines = page.split("\n")
        drop = set()
        for i in _edge_indexes(lines):
            key = _key(lines[i])
            if _PAGE_NUMBER.match(lines[i].strip()):
                drop.add(i)
            elif key in running:
                if key in kept_once:
                    drop.add(i)
                else:
                    kept_once.add(key)
        out.append("\n".join(line for i, line in enumerate(lines) if i not in drop))
    return out


def normalize_document(pages: Sequence[str]) -> list[str]:
    """Normalised index text for each page of one document, in order. A page that would become empty keeps its text."""
    folded = [fold_ligatures(page) for page in pages]
    stripped = folded
    for _ in range(3):                      # a third header line becomes an edge once the first two are gone
        again = strip_running_lines(stripped)
        if again == stripped:
            break
        stripped = again
    unstacked = [unstack_lines(page) for page in dehyphenate(stripped)]
    return [text.strip() or original for text, original in zip(unstacked, folded)]
