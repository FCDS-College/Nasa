"""Answer support check: numbers, quantities and identifiers in an answer must be traceable to the evidence it cites."""
from ai.rag.verification.support import check_answer_support

P1 = {"id": "E1", "text": "In test FX-0042 the flame speed was 3.2 cm/s at 760 mmHg with 21 % oxygen. Flow was 1,200 sccm."}
P2 = {"id": "E2", "text": "A second report measured 9.9 cm/s at 0.5 atm."}


def _unsupported(answer, passages=(P1, P2), cited=None, question=""):
    report = check_answer_support(answer, list(passages), cited_ids=cited, question=question)
    return [item.text for item in report.unsupported]


def test_a_value_present_in_the_cited_evidence_is_supported():
    assert _unsupported("The flame speed was 3.2 cm/s.", cited=["E1"]) == []


def test_a_fabricated_value_is_flagged():
    assert _unsupported("The flame speed was 5.7 cm/s.", cited=["E1"]) == ["5.7 cm/s"]


def test_a_unit_conversion_of_a_supported_value_is_supported():
    assert _unsupported("The pressure was about 101.3 kPa.", cited=["E1"]) == []


def test_a_value_that_is_only_in_an_uncited_passage_is_flagged():
    assert _unsupported("It reached 9.9 cm/s.", cited=["E1"]) == ["9.9 cm/s"]


def test_without_citations_every_passage_counts():
    assert _unsupported("It reached 9.9 cm/s.", cited=None) == []


def test_a_bare_number_must_appear_in_the_evidence():
    assert _unsupported("There were 0.35 mol of fuel.", cited=["E1"]) == ["0.35"]
    assert _unsupported("The flow was 1200.", cited=["E1"]) == []          # thousands separator in the source


def test_small_whole_numbers_and_list_markers_are_not_checked():
    assert _unsupported("Two tests were run.\n1. First point\n2. Second point with 3 samples", cited=["E1"]) == []


def test_numbered_list_markers_above_ten_are_not_checked():
    assert _unsupported("12. Twelfth point.\n13) Thirteenth point", cited=["E1"]) == []
    assert _unsupported("Point 12 is wrong.", cited=["E1"]) == ["12"]


def test_numbers_repeated_from_the_question_are_not_flagged():
    assert _unsupported("At 4.4 atm the evidence says nothing.", cited=["E1"], question="What happens at 4.4 atm?") == []


def test_a_percent_sign_with_or_without_a_space_matches():
    assert _unsupported("Oxygen was 21%.", cited=["E1"]) == []


def test_a_value_inside_a_range_in_the_evidence_is_supported():
    passages = [{"id": "E3", "text": "Speeds of 2-4 cm/s were typical."}]
    assert _unsupported("About 3 cm/s.", passages=passages, cited=["E3"]) == []
    assert _unsupported("About 6 cm/s.", passages=passages, cited=["E3"]) == ["6 cm/s"]


def test_an_identifier_not_in_the_evidence_is_flagged():
    assert _unsupported("In test FX-0099 it burned.", cited=["E1"]) == ["FX-0099"]
    assert _unsupported("In test FX-0042 it burned.", cited=["E1"]) == []


def test_the_report_counts_what_it_checked():
    report = check_answer_support("The flame speed was 3.2 cm/s and 5.7 cm/s.", [P1], cited_ids=["E1"])
    assert report.checked == 2 and len(report.unsupported) == 1 and not report.supported
    assert check_answer_support("No numbers here.", [P1]).checked == 0


def test_the_self_check_perturbs_a_figure_and_splits_sentences():
    from ai.rag.evaluation.support_selfcheck import _perturb, sentences

    assert _perturb("The flame speed was 3.2 cm/s.") == "The flame speed was 3.5 cm/s."
    assert _perturb("No figures here.") is None
    assert sentences("Too short 5. The flame speed was measured as 3.2 cm/s in the chamber. Next one!") == [
        "The flame speed was measured as 3.2 cm/s in the chamber."]


# --- named things (fuels, materials, oxidizers, instruments, platforms), not just figures --------------------------------------

def test_a_fuel_named_in_the_answer_but_absent_from_the_cited_evidence_is_flagged():
    passages = [{"id": "E9", "text": "Methane flames were imaged with a high-speed camera in the drop tower."}]
    report = check_answer_support("Propane burned more slowly.", passages, cited_ids=["E9"])
    assert [(u.text, u.kind) for u in report.unsupported] == [("Propane", "term")]
    assert check_answer_support("Methane burned more slowly.", passages, cited_ids=["E9"]).supported


def test_an_alias_of_a_supported_name_is_supported():
    passages = [{"id": "E9", "text": "Samples of PMMA were burned."}]
    assert check_answer_support("The acrylic samples burned.", passages, cited_ids=["E9"]).supported
    assert not check_answer_support("The cellulose samples burned.", passages, cited_ids=["E9"]).supported


def test_a_name_in_the_question_or_only_in_an_uncited_passage():
    passages = [{"id": "E1", "text": "Ethanol pool fires were studied."}, {"id": "E2", "text": "Hydrogen jets were studied."}]
    assert check_answer_support("Hydrogen was not covered.", passages, cited_ids=["E1"], question="What about hydrogen?").supported
    assert [u.text for u in check_answer_support("Hydrogen was used.", passages, cited_ids=["E1"]).unsupported] == ["Hydrogen"]


def test_generic_words_and_physical_quantities_are_not_checked_as_names():
    passages = [{"id": "E1", "text": "The flame was photographed."}]
    assert check_answer_support("Ignition and extinction pressure were discussed; the temperature rose.", passages, cited_ids=["E1"]).supported


def test_report_separates_figures_from_names():
    report = check_answer_support("Propane burned at 9.9 cm/s.", [{"id": "E1", "text": "Methane burned at 3.2 cm/s."}], cited_ids=["E1"])
    assert {u.kind for u in report.unsupported} == {"term", "measurement"}
    assert [u.text for u in report.figures] == ["9.9 cm/s"] and [u.text for u in report.terms] == ["Propane"]


def test_the_self_check_swaps_a_name_for_one_the_page_never_mentions():
    from ai.rag.evaluation.support_selfcheck import _swap_term

    swapped = _swap_term("Methane flames were imaged.", "Methane flames were imaged with a camera.")
    assert swapped is not None and "Methane" not in swapped and swapped.endswith("flames were imaged.")
    assert _swap_term("No named thing here.", "anything") is None
