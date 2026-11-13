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


# ---------------------------------------------------------------- audit finding 3: notation the corpus actually uses

def _one(text):
    [record] = _extract(text)
    return record.payload


def test_g_written_against_the_number_is_gravity_not_grams():
    payload = _one("the 1g upward flame spread test")
    assert payload["dimension"] == "acceleration" and payload["value_si"] == pytest.approx(9.80665)
    assert payload["si_unit"] == "m/s^2"


def test_g_followed_by_of_is_grams():
    payload = _one("approximately 700 g of fuel")
    assert payload["dimension"] == "mass" and payload["value_si"] == pytest.approx(0.7)


@pytest.mark.parametrize("text", ["flames in 1 g and microgravity", "nominally ±0.02 g for a ~20 s duration"])
def test_a_bare_g_is_ambiguous_and_never_converted_to_kilograms(text):
    g = [r.payload for r in _extract(text) if r.payload["unit"] == "g"][0]
    assert g["dimension"] == "gravity_or_mass" and g["si_unit"] == "g" and g["value_si"] == g["value"]


def test_mm_hg_with_a_space_is_pressure():
    payload = _one("cabin at 760 mm Hg")
    assert payload["dimension"] == "pressure" and payload["value_si"] == pytest.approx(101325.0, rel=1e-6)


@pytest.mark.parametrize("text,si,unit", [("5 x 10^-3 m", 0.005, "m"), ("5 × 10^-3 m", 0.005, "m"),
                                          ("10^-6 s", 1e-6, "s"), ("1,000 Pa", 1000.0, "Pa"),
                                          ("9.8 m/s^2", 9.8, "m/s^2"), ("9.8 m/s²", 9.8, "m/s^2"),
                                          ("200 °F", 366.483, "K")])
def test_scientific_notation_thousands_acceleration_and_fahrenheit(text, si, unit):
    payload = _one(text)
    assert payload["value_si"] == pytest.approx(si, rel=1e-4) and payload["si_unit"] == unit


@pytest.mark.parametrize("text", ["an area of 5 cm^2", "MOVEMENT BEGINNING 23:30:3g.5 ENDING"])
def test_areas_and_ocr_timestamps_are_not_misread(text):
    assert _extract(text) == []


def test_a_footnote_marker_after_a_unit_does_not_hide_the_measurement():
    assert _one("a pressure differential of 1.05 atm.13,14 Using")["value_si"] == pytest.approx(106391.25)


@pytest.mark.parametrize("text", ["near 10-6 g in orbit", "levels of 10-4 g"])
def test_a_flattened_superscript_exponent_is_not_read_as_a_descending_range(text):
    assert _extract(text) == []


def test_an_ascending_hyphen_range_is_still_a_range():
    payload = _one("tested at 70-101 kPa")
    assert payload["value"] == 70 and payload["value_max"] == 101
