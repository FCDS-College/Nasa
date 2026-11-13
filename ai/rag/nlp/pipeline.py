"""Run every extractor over one chunk, then the cross-record steps (measurement linking, condition promotion)."""
from __future__ import annotations

from ai.rag.nlp.records import ChunkInput, Extractor, NlpRecord, run_extractors
from ai.rag.nlp.vocab import link_measurements, promote_conditions


def extract_chunk(chunk: ChunkInput, extractors: list[Extractor]) -> tuple[list[NlpRecord], dict[str, int]]:
    records, dropped = run_extractors(chunk, extractors)
    records = link_measurements(chunk, records)
    return [*records, *promote_conditions(records)], dropped
