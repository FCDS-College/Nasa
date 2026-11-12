"""ADR-006: the ai/rag search stack (rewrite, RRF, reranked window, paging)."""
import pytest

from ai.rag.retrieval.search_stack import Candidate, RerankUnavailable, SearchStack


def candidates():
    return [
        Candidate("c1", "document", "flame spread over nomex", {"lexical": 1, "dense": 3}),
        Candidate("c2", "document", "droplet extinction", {"lexical": 2}),
        Candidate("c3", "document", "soot in a laminar jet", {"dense": 1}),
        Candidate("e1", "experiment", "FLEX 193F001", {"experiment_lexical": 1}),
        Candidate("c4", "document", "unrelated", {"lexical": 3}),
    ]


def test_fusion_is_reciprocal_rank_fusion_with_a_deterministic_tie_break():
    ranked, outcome = SearchStack().rank("flame", candidates())

    assert outcome.status == "disabled"
    # c3 (dense 1) and e1 (experiment list 1) tie at 1/61: the document sorts first; then c2 (1/62), c4 (1/63).
    assert [item.candidate.result_id for item in ranked] == ["c1", "c3", "e1", "c2", "c4"]
    assert [item.score for item in ranked] == pytest.approx([1 / 61 + 1 / 63, 1 / 61, 1 / 61, 1 / 62, 1 / 63])
    assert [item.score for item in ranked] == sorted((item.score for item in ranked), reverse=True)


def test_duplicate_or_zero_based_candidates_are_refused():
    with pytest.raises(ValueError):
        SearchStack().fuse([Candidate("x", "document", "", {"lexical": 1})] * 2)
    with pytest.raises(ValueError):
        SearchStack().fuse([Candidate("x", "document", "", {"lexical": 0})])


def test_reranking_reorders_only_the_window_and_keeps_scores_monotonic():
    calls = []

    def rerank(query, documents):
        calls.append((query, [doc_id for doc_id, _ in documents]))
        scores = {doc_id: (10.0 if "FLEX" in text else 0.0) for doc_id, text in documents}
        return scores, "fake-cross-encoder"

    fused, _ = SearchStack().rank("FLEX droplet", candidates())
    ranked, outcome = SearchStack(rerank=rerank, rerank_depth=3).rank("FLEX droplet", candidates())

    assert outcome.as_dict() == {"status": "applied", "model": "fake-cross-encoder", "depth": 3}
    assert calls == [("FLEX droplet", ["c1", "c3", "e1"])]
    # e1 moves to the top of the window; c1 and c3 tie at 0 and keep their fused order.
    assert [item.candidate.result_id for item in ranked[:3]] == ["e1", "c1", "c3"] and ranked[0].rerank_score == 10.0
    # The window keeps its own fused scores as slots; nothing after it moves.
    assert [item.score for item in ranked[:3]] == [item.fused_score for item in fused[:3]]
    assert [item.candidate.result_id for item in ranked[3:]] == [item.candidate.result_id for item in fused[3:]]
    assert [item.score for item in ranked] == sorted((item.score for item in ranked), reverse=True)


def test_a_failing_reranker_keeps_the_fused_order():
    def broken(query, documents):
        raise RerankUnavailable("model missing")

    def partial(query, documents):
        return {documents[0][0]: 1.0}, "fake"

    fused, _ = SearchStack().rank("flame", candidates())
    for reranker in (broken, partial):
        ranked, outcome = SearchStack(rerank=reranker).rank("flame", candidates())
        assert outcome.status == "unavailable"
        assert [item.candidate.result_id for item in ranked] == [item.candidate.result_id for item in fused]


def test_pages_are_slices_of_one_order_so_paging_is_exact():
    def rerank(query, documents):
        return {doc_id: float(len(text)) for doc_id, text in documents}, "fake"

    stack = SearchStack(rerank=rerank, rerank_depth=4)
    ranked, _ = stack.rank("flame", candidates())
    pages = [stack.page(ranked, page, 2) for page in (1, 2, 3)]

    assert [rank for page in pages for rank, _ in page] == [1, 2, 3, 4, 5]
    assert [item.candidate.result_id for page in pages for _, item in page] == [i.candidate.result_id for i in ranked]


def test_the_plan_keeps_the_original_for_lexical_and_embeds_the_rewrite():
    plan = SearchStack().plan("ISS  cabin fires")

    assert plan.lexical_query == "ISS  cabin fires"
    assert plan.semantic_query == "ISS (international space station) cabin fires"
    assert plan.as_dict() == {"rewritten": "ISS (international space station) cabin fires", "changed": True,
                              "rules_applied": ["normalize_whitespace", "expand:iss"], "rewriter_version": "1.0.0",
                              "used_for": ["semantic"]}
    assert SearchStack().plan("flame spread").as_dict()["changed"] is False
