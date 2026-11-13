import pytest

from ai.rag.nlp.quantities import MeasurementExtractor
from ai.rag.nlp.records import ChunkInput
from ai.rag.nlp.units import to_si


def _extract(text):
    return MeasurementExtractor().extract(ChunkInput("c-1", "d-1", "v1", 1, text))


def test_velocity_uses_the_longest_unit_and_converts():
    text = "In run FX-0042 the flame speed was 3.2 cm/s at 0.1 atm."
    first, second = _extract(text)
    assert first.text == "3.2 cm/s" and first.char_start == text.index("3.2 cm/s")
    assert first.payload["value_si"] == pytest.approx(0.032) and first.payload["si_unit"] == "m/s"
    assert second.text == "0.1 atm" and second.payload["dimension"] == "pressure"


def test_range_is_one_record():
    [record] = _extract("tested at 0.1–0.3 atm")
    assert record.payload["value"] == 0.1 and record.payload["value_max"] == 0.3
    assert record.payload["value_si"] == pytest.approx(10132.5) and record.payload["value_si_max"] == pytest.approx(30397.5)


@pytest.mark.parametrize("text,si", [("21 %", 0.21), ("−5 °C", 268.15), ("2e-3 s", 0.002)])
def test_percent_negative_and_exponent_parse(text, si):
    [record] = _extract(text)
    assert record.payload["value_si"] == pytest.approx(si)


@pytest.mark.parametrize("text", ["3 sample", "12 months", "run 7 later", "no numbers here"])
def test_non_measurements_are_not_extracted(text):
    assert _extract(text) == []


def test_mmhg_matches_the_ingest_factor_and_torr_is_exactly_one_760th_of_an_atmosphere():
    # 133.322387415 is the factor flame_api.ingest.convert_to_si applies to the committed NASA tables.
    assert to_si(1, "mmHg") == (133.322387415, "Pa")
    assert to_si(760, "Torr") == (pytest.approx(101325.0, rel=1e-12), "Pa")
    assert to_si(760, "mmHg")[0] == pytest.approx(101325.0, rel=1e-6)   # mmHg and Torr differ by ~1.4e-7
