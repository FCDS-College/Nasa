import pytest

from ai.rag.nlp.records import ChunkInput, NlpRecord, run_extractors, span_record

CHUNK = ChunkInput("c-1", "d-1", "v1", 3, "In run FX-0042 the flame speed was 3.2 cm/s at 0.1 atm.")


class _Fake:
    name, version, method = "fake", "1.0.0", "rule"

    def __init__(self, spans):
        self.spans = spans

    def extract(self, chunk):
        return [span_record(self, chunk, "experiment", s, e) for s, e in self.spans]


def _record(**over):
    base = dict(record_type="experiment", text="FX-0042", document_id="d-1", document_version="v1", page=3, char_start=7,
                char_end=14, chunk_id="c-1", extractor="fake", extractor_version="1.0.0", method="rule", confidence=1.0)
    return NlpRecord(**{**base, **over})


@pytest.mark.parametrize("over", [{"char_end": 7}, {"char_start": -1}, {"chunk_id": ""}, {"confidence": 1.5},
                                  {"review_status": "verified"}])
def test_invalid_record_is_rejected(over):
    with pytest.raises(ValueError):
        _record(**over)


def test_span_record_copies_text_from_the_chunk():
    record = span_record(_Fake([]), CHUNK, "experiment", 7, 14)
    assert record.text == "FX-0042" and record.page == 3 and record.review_status == "machine_extracted"


def test_record_id_is_stable_and_version_sensitive():
    assert _record().record_id == _record().record_id
    assert _record().record_id != _record(extractor_version="1.0.1").record_id
    assert _record().record_id != _record(char_end=15, text="FX-0042 ").record_id


def test_run_extractors_drops_and_counts_spans_not_in_the_chunk():
    class Liar(_Fake):
        name = "liar"

        def extract(self, chunk):
            return [_record(extractor="liar", text="FX-9999")]   # span 7:14 is "FX-0042"

    kept, dropped = run_extractors(CHUNK, [_Fake([(7, 14)]), Liar([])])
    assert [r.text for r in kept] == ["FX-0042"] and dropped == {"liar": 1}
