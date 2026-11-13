from ai.rag.nlp.identifiers import IdentifierExtractor
from ai.rag.nlp.records import ChunkInput


def _extract(text):
    return IdentifierExtractor().extract(ChunkInput("c-1", "d-1", "v1", 1, text))


def test_experiment_id_span():
    [record] = _extract("In run FX-0042 the flame speed was 3.2 cm/s at 0.1 atm.")
    assert (record.record_type, record.text, record.char_start, record.char_end) == ("experiment", "FX-0042", 7, 14)


def test_publication_pattern_wins_over_experiment_pattern():
    records = _extract("See NASA/TM-2008-215260 and dataset PSI-69.")
    assert [(r.record_type, r.normalized) for r in records] == [("publication", "NASA/TM-2008-215260"), ("dataset", "PSI-69")]


def test_ntrs_doi_and_spaced_report_number_are_normalised():
    records = _extract("FF-NTRS-20080034883, doi 10.1016/J.Combustflame.2008.01.001, NASA TM-2000-209773.")
    assert [r.normalized for r in records] == ["FF-NTRS-20080034883", "10.1016/j.combustflame.2008.01.001", "NASA/TM-2000-209773"]


def test_experiment_id_needs_a_context_word_and_the_span_excludes_it():
    [record] = _extract("Results for Test #HT90-40 were repeated.")
    assert record.text == "HT90-40" and record.char_start == len("Results for Test #")


def test_standards_missions_and_conference_ids_are_not_experiments():
    # Measured on the committed NTRS PDFs: these were the most frequent false positives of a context-free pattern.
    text = "NASA-STD-6001 Test 1 on STS-94 aboard a KC-135, see AIAA-2005-1234 and IAC-12 for details."
    assert [r for r in _extract(text) if r.record_type == "experiment"] == []


def test_plain_prose_has_no_identifiers():
    assert _extract("The flame spread more slowly at reduced pressure.") == []
