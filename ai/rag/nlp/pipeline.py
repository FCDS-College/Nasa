"""Run every extractor over one chunk, then the cross-record steps (measurement linking, condition promotion)."""
from __future__ import annotations

from ai.rag.nlp.records import ChunkInput, Extractor, NlpRecord, run_extractors
from ai.rag.nlp.vocab import link_measurements, promote_conditions


def extract_chunk(chunk: ChunkInput, extractors: list[Extractor]) -> tuple[list[NlpRecord], dict[str, int]]:
    records, dropped = run_extractors(chunk, extractors)
    records = link_measurements(chunk, records)
    return [*records, *promote_conditions(records)], dropped


# Records produced by a later step of `extract_chunk`, not by an extractor in the list. A runner that reconciles stored records
# by extractor name must include them, or they could never be superseded.
DERIVED_EXTRACTORS = ("condition-rules",)


def default_extractors(vocabulary: dict) -> list[Extractor]:
    """The deterministic extractors (everything except LLM spans, which are opt-in)."""
    from ai.rag.nlp.classify import DocumentClassifier, MetadataExtractor
    from ai.rag.nlp.figures import FigureTableExtractor
    from ai.rag.nlp.identifiers import IdentifierExtractor
    from ai.rag.nlp.quantities import MeasurementExtractor
    from ai.rag.nlp.vocab import VocabularyExtractor, vocabulary_version

    return [IdentifierExtractor(), MeasurementExtractor(), DocumentClassifier(), MetadataExtractor(), FigureTableExtractor(),
            VocabularyExtractor(vocabulary, version=vocabulary_version(vocabulary))]
