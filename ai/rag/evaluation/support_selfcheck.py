"""Self-check of the answer support checker on real page text (not an accuracy measurement).

    python -m ai.rag.evaluation.support_selfcheck docs/research [--limit N]

For every sentence on the indexed pages that states a measurement or a multi-digit number:
  * as written (a perfectly supported "answer", the page as the cited passage): how often is it flagged? (false positives)
  * with one digit of its first figure changed (a fabricated figure): how often is it flagged? (detection)
Both rates come with a 95 % bootstrap interval over sentences. Sentences are not independent samples of what a language model
writes, so read the rates as "does the checker behave sensibly on real scientific prose", not as its precision or recall on answers.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ai.rag.evaluation.propose_candidates import indexed_pages
from ai.rag.evaluation.stats import bootstrap_ci
from ai.rag.verification.support import CHECK_VERSION, check_answer_support

_FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _perturb(sentence: str) -> str | None:
    """Change the last digit of the first figure the checker would look at, so the value can no longer occur in the page."""
    for match in _FIGURE.finditer(sentence):
        token = match.group(0)
        if len(token.replace(",", "").replace(".", "")) < 2 and "." not in token:
            continue
        digit = token[-1]
        if not digit.isdigit():
            continue
        changed = token[:-1] + str((int(digit) + 3) % 10)
        return sentence[:match.start()] + changed + sentence[match.end():]
    return None


def _swap_term(sentence: str, page_text: str) -> str | None:
    """Replace the first controlled-vocabulary name in `sentence` with another name of the same type that the page never mentions."""
    from ai.rag.verification.support import _default_term_extractor

    extractor = _default_term_extractor()
    records = extractor.extract(_chunk_of(sentence))
    if not records:
        return None
    first = records[0]
    page_lower = page_text.lower()
    from ai.rag.nlp.vocab import load_vocabulary

    candidates = [name for name in load_vocabulary()[first.record_type] if name != first.normalized and name.lower() not in page_lower]
    if not candidates:
        return None
    return sentence[:first.char_start] + sorted(candidates)[0] + sentence[first.char_end:]


def _chunk_of(text: str):
    from ai.rag.nlp.records import ChunkInput

    return ChunkInput("selfcheck", "selfcheck", "v1", None, text)


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat) if 25 <= len(s) <= 400 and _FIGURE.search(s)]


def run(pdf_dir: Path, limit: int | None = None) -> dict:
    flagged_as_written, flagged_perturbed, n = [], [], 0
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        for page in indexed_pages(path):
            passage = [{"id": "P", "text": page["indexed"]}]
            for sentence in sentences(page["indexed"]):
                perturbed = _perturb(sentence)
                if perturbed is None:
                    continue
                if check_answer_support(sentence, passage, cited_ids=["P"]).checked == 0:
                    continue          # nothing the checker looks at, e.g. only small integers
                n += 1
                flagged_as_written.append(1.0 if not check_answer_support(sentence, passage, cited_ids=["P"]).supported else 0.0)
                flagged_perturbed.append(1.0 if not check_answer_support(perturbed, passage, cited_ids=["P"]).supported else 0.0)
                if limit and n >= limit:
                    break
            if limit and n >= limit:
                break
    term_written, term_swapped = [], []
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        for page in indexed_pages(path):
            passage = [{"id": "P", "text": page["indexed"]}]
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", re.sub(r"\s+", " ", page["indexed"])):
                if not 25 <= len(sentence) <= 400:
                    continue
                swapped = _swap_term(sentence, page["indexed"])
                if swapped is None:
                    continue
                term_written.append(1.0 if check_answer_support(sentence, passage, cited_ids=["P"]).terms else 0.0)
                term_swapped.append(1.0 if check_answer_support(swapped, passage, cited_ids=["P"]).terms else 0.0)
    def summary(values: list[float]) -> dict:
        if not values:
            return {"rate": None}
        low, high = bootstrap_ci(values)
        return {"rate": round(sum(values) / len(values), 4), "ci95": [round(low, 4), round(high, 4)]}
    return {"checker": CHECK_VERSION, "sentences": n, "false_positive_rate": summary(flagged_as_written),
            "detection_rate_on_perturbed_figures": summary(flagged_perturbed),
            "term_sentences": len(term_written), "term_false_positive_rate": summary(term_written),
            "term_detection_rate_on_swapped_names": summary(term_swapped)}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.pdf_dir, args.limit), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
