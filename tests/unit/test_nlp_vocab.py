import pytest

from ai.rag.nlp.pipeline import extract_chunk
from ai.rag.nlp.quantities import MeasurementExtractor
from ai.rag.nlp.records import ChunkInput
from ai.rag.nlp.vocab import VocabularyExtractor, load_vocabulary, vocabulary_version

VOCAB = {
    "fuel": {"n-heptane": ["heptane", "C7H16"]},
    "platform": {"International Space Station": [{"text": "ISS", "case_sensitive": True}]},
    "physical_quantity": {"flame speed": [], "pressure": []},
    "environmental_condition": {"microgravity": ["micro-gravity"]},
}


def _chunk(text):
    return ChunkInput("c-1", "d-1", "v1", 1, text)


def _extractors():
    return [MeasurementExtractor(), VocabularyExtractor(VOCAB, version=vocabulary_version(VOCAB))]


def test_longest_match_and_alias_normalisation():
    records = VocabularyExtractor(VOCAB, "v").extract(_chunk("n-heptane (C7H16) was burned"))
    assert [(r.text, r.normalized) for r in records] == [("n-heptane", "n-heptane"), ("C7H16", "n-heptane")]


def test_short_case_insensitive_alias_is_refused():
    with pytest.raises(ValueError):
        VocabularyExtractor({"platform": {"International Space Station": ["IS"]}}, "v")


def test_case_sensitive_alias():
    extractor = VocabularyExtractor(VOCAB, "v")
    assert [r.text for r in extractor.extract(_chunk("aboard the ISS"))] == ["ISS"]
    assert extractor.extract(_chunk("the iss module")) == []


def test_measurement_is_linked_to_the_nearest_quantity():
    records, dropped = extract_chunk(_chunk("The flame speed was 3.2 cm/s."), _extractors())
    measurement = next(r for r in records if r.record_type == "measurement")
    assert measurement.payload["quantity"] == "flame speed" and dropped == {}


def test_conditions_are_promoted():
    records, _ = extract_chunk(_chunk("Tests at 0.1 atm in microgravity."), _extractors())
    conditions = sorted(r.text for r in records if r.record_type == "environmental_condition")
    assert conditions == ["0.1 atm", "microgravity"]


def test_vocabulary_version_changes_with_content():
    assert vocabulary_version(VOCAB) != vocabulary_version({**VOCAB, "fuel": {"methane": []}})


def test_seed_vocabularies_load_and_have_no_duplicate_aliases():
    vocabulary = load_vocabulary()
    for record_type, entries in vocabulary.items():
        seen: dict[str, str] = {}
        for canonical, aliases in entries.items():
            for alias in [canonical, *[a if isinstance(a, str) else a["text"] for a in aliases]]:
                assert seen.setdefault(alias.lower(), canonical) == canonical, (record_type, alias)


def test_an_acronym_that_is_also_a_word_is_only_matched_in_its_own_case():
    # Investigation names such as SAME or FLEX are common English words in lower case. When the entry gives the canonical name
    # as a case-sensitive alias, the canonical must not also be matched case-insensitively.
    vocabulary = {"investigation": {"SAME": [{"text": "SAME", "case_sensitive": True}]}}
    extractor = VocabularyExtractor(vocabulary, "v")
    assert extractor.extract(_chunk("The same sample was used in the same run.")) == []
    assert [r.text for r in extractor.extract(_chunk("The SAME experiment flew."))] == ["SAME"]


def test_a_canonical_with_no_explicit_alias_is_still_matched_case_insensitively():
    extractor = VocabularyExtractor({"fuel": {"methane": []}}, "v")
    assert [r.text for r in extractor.extract(_chunk("Methane and METHANE"))] == ["Methane", "METHANE"]
