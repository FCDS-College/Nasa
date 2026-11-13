"""Table-aware indexing text (audit roadmap item 12).

Plain page text reads a table in layout order, so "which value goes with which column" is lost. PyMuPDF's `find_tables` recovers cells;
this module renders a table as one `Header=value; Header=value` line per row, appended to the page's *index* text (never to the evidence
excerpt, which stays verbatim).

Measured on the 24 committed NTRS PDFs (old reports, scanned or OCR'd text layers) most detected tables have broken cells: decimal points
split onto a second line (`165\\n.` for 16.5), merged cells, dotted leaders. A rendered row built from those would state wrong values with
confidence, so a table is rendered only if nearly all of its cells are clean (`MIN_CLEAN_SHARE`); everything else is left to the page text.
"""
from __future__ import annotations

import re
from typing import Any, Sequence

MIN_CLEAN_SHARE = 0.9
MIN_ROWS = 3
MIN_COLUMNS = 2
_SPACE = re.compile(r"\s+")


def _cell(value: Any) -> str:
    return _SPACE.sub(" ", str(value)).strip() if value is not None else ""


def _broken(raw: Any) -> bool:
    """A cell a line break has split: some line of it holds no letter or digit (`165` / `.`), the mark of a damaged text layer.

    A cell that merely wraps (`burned` / `fully`) is fine, and so is an empty one.
    """
    if raw is None:
        return False
    lines = [line.strip() for line in str(raw).split("\n") if line.strip()]
    return any(not any(ch.isalnum() for ch in line) for line in lines)


def render_table(rows: Sequence[Sequence[Any]]) -> str | None:
    """`Header=value; ...` per data row, or None when the table is too small or its cells are not trustworthy."""
    if not rows:
        return None
    width = max(len(r) for r in rows)
    grid = [[r[i] if i < len(r) else None for i in range(width)] for r in rows]
    keep_columns = [i for i in range(width) if any(_cell(r[i]) for r in grid)]
    grid = [[r[i] for i in keep_columns] for r in grid]
    grid = [r for r in grid if any(_cell(c) for c in r)]
    if len(grid) < MIN_ROWS or len(grid[0]) < MIN_COLUMNS:
        return None
    header = [_cell(c) for c in grid[0]]
    named = [h for h in header if h]
    if len(named) < MIN_COLUMNS or len(set(named)) != len(named):
        return None
    cells = [c for r in grid for c in r if _cell(c)]
    if not cells or sum(not _broken(c) for c in cells) / len(cells) < MIN_CLEAN_SHARE:
        return None
    lines = []
    for row in grid[1:]:
        parts = [f"{header[i]}={_cell(row[i])}" for i in range(len(header)) if header[i] and _cell(row[i])]
        if parts:
            lines.append("; ".join(parts))
    return "\n".join(lines) or None


def table_texts(page: Any) -> str:
    """Rendered text of the trustworthy tables on a PyMuPDF page, separated by blank lines; "" when none or detection fails."""
    try:
        tables = page.find_tables().tables
        rendered = [text for table in tables if (text := render_table(table.extract()))]
    except Exception:    # table detection is optional: a failure must never cost the page its text
        return ""
    return "\n\n".join(rendered)
