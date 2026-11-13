from ai.rag.nlp.classify import DocumentClassifier, MetadataExtractor
from ai.rag.nlp.records import ChunkInput

PAGE1 = ("NASA/TM-2008-215260\n\nMicrogravity Flame Spread\n\nAugust 2008\n\nAbstract\nFlame spread was measured at "
         "several pressures.\n\nIntroduction\nText.")


def _chunk(text, page=1):
    return ChunkInput("c-1", "d-1", "v1", page, text)


def test_technical_report_cue():
    [record] = DocumentClassifier().extract(_chunk(PAGE1))
    assert (record.normalized, record.confidence, record.text) == ("technical_report", 1.0, "NASA/TM-")


def test_two_label_cues_lower_the_confidence():
    [record] = DocumentClassifier().extract(_chunk("NASA/TM-2008-215260 Proceedings of the Workshop"))
    assert (record.normalized, record.confidence) == ("technical_report", 0.5)


def test_metadata_fields_and_abstract_span():
    fields = {r.payload["field"]: r for r in MetadataExtractor().extract(_chunk(PAGE1))}
    assert fields["report_number"].normalized == "NASA/TM-2008-215260" and fields["year"].normalized == "2008"
    assert fields["abstract"].text == "Flame spread was measured at several pressures."


def test_only_page_one_is_classified():
    assert DocumentClassifier().extract(_chunk(PAGE1, page=2)) == []
    assert MetadataExtractor().extract(_chunk(PAGE1, page=None)) == []
