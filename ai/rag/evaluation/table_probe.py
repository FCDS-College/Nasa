"""How many tables does PyMuPDF find in a folder of PDFs, and how many would `render_table` accept? (audit roadmap item 12)

    python -m ai.rag.evaluation.table_probe docs/research [--show N]

Prints counts and the first N rendered tables so a person can judge them. Whether a rendered table is a real data table is a human
call; the committed NTRS reports give mostly text boxes (preprint notices, address blocks) and damaged data tables.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai.rag.ingestion.tables import MIN_CLEAN_SHARE, render_table


def probe(pdf_dir: Path, show: int = 0) -> dict:
    import pymupdf

    pages = found = rendered = pages_with_rendered = 0
    examples = []
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        for number, page in enumerate(pymupdf.open(path), start=1):
            pages += 1
            kept = False
            for table in page.find_tables().tables:
                found += 1
                text = render_table(table.extract())
                if text:
                    rendered += 1
                    kept = True
                    if len(examples) < show:
                        examples.append({"file": path.name, "page": number, "text": text[:400]})
            pages_with_rendered += kept
    return {"pages": pages, "tables_found": found, "tables_rendered": rendered, "pages_with_a_rendered_table": pages_with_rendered,
            "min_clean_share": MIN_CLEAN_SHARE, "examples": examples}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("--show", type=int, default=0)
    args = parser.parse_args(argv)
    print(json.dumps(probe(args.pdf_dir, args.show), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
