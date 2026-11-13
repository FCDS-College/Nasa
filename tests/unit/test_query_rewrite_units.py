"""`psi` is a pressure unit far more often than NASA's PSI programme (audit finding R-1)."""
import pytest

from ai.rag.query.rewrite import QueryRewriter


@pytest.mark.parametrize("query", [
    "Flame spread at 14.7 psi",
    "burning at 101 kPa (14.7 PSI) pressure",
    "Does extinction change between 5 and 30 psi?",
    "pressure of 14.7-psi cabin air",
    "from 10 psi to 20 psi",
])
def test_a_pressure_unit_after_a_number_is_not_expanded(query):
    rewritten = QueryRewriter().rewrite(query)
    assert rewritten.rewritten == query and "expand:psi" not in rewritten.rules_applied


def test_the_programme_name_is_still_expanded():
    rewritten = QueryRewriter().rewrite("What PSI data exists for FLEX?")
    assert rewritten.rewritten == "What PSI (physical sciences informatics) data exists for FLEX?"
    assert "expand:psi" in rewritten.rules_applied


def test_the_unit_is_skipped_but_a_later_programme_mention_is_expanded():
    rewritten = QueryRewriter().rewrite("At 14.7 psi, which PSI datasets cover it?")
    assert rewritten.rewritten == "At 14.7 psi, which PSI (physical sciences informatics) datasets cover it?"


def test_other_abbreviations_are_unaffected_by_numbers():
    assert QueryRewriter().rewrite("ISS experiment 12").rewritten == "ISS (international space station) experiment 12"


def test_the_rewriter_version_records_that_behaviour_changed():
    assert QueryRewriter().rewrite("flame").rewriter_version == "1.0.1"
