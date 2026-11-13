"""Lexical leg without the AND wall: terms, inverse document frequency and the OR query text (audit roadmap item 10)."""
import math

from ai.rag.retrieval.lexical_query import bm25_idf, or_tsquery_text, query_terms


def test_stopwords_are_dropped_and_domain_tokens_survive():
    assert query_terms("What is the flame speed of PMMA in O2 and He?") == ["flame", "speed", "pmma", "o2", "he"]


def test_terms_are_deduplicated_lower_cased_and_capped():
    assert query_terms("Flame flame FLAME") == ["flame"]
    assert len(query_terms(" ".join(f"term{i}" for i in range(30)), max_terms=8)) == 8


def test_longer_and_rarer_looking_terms_are_kept_when_the_cap_bites():
    terms = query_terms("a b c flammability d e f g h i j k l m heptane", max_terms=2)
    assert terms == ["flammability", "heptane"]


def test_hyphenated_and_decimal_tokens_stay_whole():
    assert query_terms("n-heptane at 0.1 atm") == ["n-heptane", "0.1", "atm"]


def test_idf_gives_rare_terms_more_weight_and_never_goes_negative():
    assert bm25_idf(2, 1000) > bm25_idf(500, 1000) > bm25_idf(1000, 1000) >= 0
    assert math.isclose(bm25_idf(0, 100), math.log(1 + 100.5 / 0.5))


def test_the_or_query_text_is_quoted_and_cannot_inject_operators():
    assert or_tsquery_text(["flame", "n-heptane"]) == "'flame' | 'n-heptane'"
    assert or_tsquery_text(["a'b", "c|d", "e&f", "(x)"]) == "'a b' | 'c d' | 'e f' | 'x'"
    assert or_tsquery_text([]) == ""
