"""Split a page into overlapping windows the embedder can read in full (audit roadmap item 11).

A page is one chunk, median 3,114 characters, but the embedder reads only the first `MAX_CHUNK_CHARS` (2,000) of it, so the dense leg
cannot see the rest of most pages. Windows of about 1,200 characters, overlapping by 200, cover the whole page; each is embedded on its
own and a page scores as its best window (`ai/rag/retrieval/aggregate.py`).

Pure Python. Offsets are character offsets into the text given, so `text[w.start:w.end] == w.text`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ai.providers.local.fastembed_embeddings import MAX_CHUNK_CHARS as MAX_WINDOW_CHARS

WINDOW_CHARS = 1200
WINDOW_OVERLAP = 200
_MIN_FILL = 0.6                      # a window is cut at a sentence end only if that keeps at least this share of its size
_SENTENCE_END = re.compile(r"[.!?](?=\s)")


@dataclass(frozen=True, slots=True)
class Window:
    ordinal: int
    start: int
    end: int
    text: str


def _cut(text: str, start: int, hard_end: int, size: int) -> int:
    floor = start + int(size * _MIN_FILL)
    sentence = [m.end() for m in _SENTENCE_END.finditer(text, floor, hard_end)]
    if sentence:
        return sentence[-1]
    space = max((i for i in range(floor, hard_end) if text[i].isspace()), default=None)
    return space if space is not None else hard_end


def _snap_forward(text: str, position: int, end: int) -> int:
    """Move `position` to the start of the next word, so a window does not begin in the middle of one (if there is a gap)."""
    if position <= 0 or text[position - 1].isspace():
        return position
    gap = next((i for i in range(position, end) if text[i].isspace()), None)
    if gap is None:
        return position
    while gap < end and text[gap].isspace():
        gap += 1
    return gap


def split_windows(text: str, size: int = WINDOW_CHARS, overlap: int = WINDOW_OVERLAP) -> list[Window]:
    if not 0 < size <= MAX_WINDOW_CHARS:
        raise ValueError(f"size must be 1..{MAX_WINDOW_CHARS}: the embedder reads no more")
    if not 0 <= overlap < size * _MIN_FILL:
        raise ValueError("overlap must be smaller than the least a window keeps")
    if not text.strip():
        return []
    length = len(text)
    start = next(i for i, ch in enumerate(text) if not ch.isspace())
    windows: list[Window] = []
    while start < length:
        hard_end = min(start + size, length)
        end = length if hard_end == length else _cut(text, start, hard_end, size)
        windows.append(Window(len(windows), start, end, text[start:end]))
        if end >= length:
            break
        following = _snap_forward(text, end - overlap, end)
        start = following if following > start else end
    return windows
