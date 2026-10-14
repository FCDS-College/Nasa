import pytest

from ai.rag.query.rewrite import QueryRewriter
from ai.rag.reranking.cross_encoder import CrossEncoderReranker, RerankerUnavailable
from ai.rag.retrieval.fusion import fuse_and_page, reciprocal_rank_fusion


def test_rewrite_keeps_original_and_expands():
    rq = QueryRewriter().rewrite("what is  PSI data?")
    assert rq.original == "what is  PSI data?"
    assert "physical sciences informatics" in rq.rewritten
    assert "PSI" in rq.rewritten and rq.changed


def test_rewrite_empty_raises():
    with pytest.raises(ValueError):
        QueryRewriter().rewrite("   ")


def test_rrf_rewards_agreement():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert [i for i, _ in fused][:2] == ["a", "b"] or [i for i, _ in fused][:2] == ["b", "a"]
    assert {i for i, _ in fused} == {"a", "b", "c", "d"}


def test_page_two_still_contains_semantic_only_results():
    lexical = ["l1", "l2", "l3", "l4"]
    dense = ["d1", "d2", "d3", "d4"]
    page2 = [i for i, _ in fuse_and_page([lexical, dense], page=2, page_size=3)]
    assert any(i.startswith("d") for i in page2) and any(i.startswith("l") for i in page2)


def test_rrf_validation():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], weights=[1, 2])


def _results():
    return [{"chunk": {"chunk_id": f"c{i}", "text": t}, "hybrid_score": 0.5}
            for i, t in enumerate(["irrelevant", "flame spread rate", "soot"])]


def test_reranker_orders_by_model_score_and_logs():
    rr = CrossEncoderReranker(scorer=lambda pairs: [1.0 if "flame" in t else 0.0 for _, t in pairs])
    out = rr.rerank("flame", _results(), top_k=2)
    assert out[0]["chunk"]["chunk_id"] == "c1"
    assert len(out) == 2 and rr.last_scores[0]["reranker_version"] == "1.0.0"


def test_reranker_failure_raises_no_silent_fallback():
    def boom(pairs):
        raise RuntimeError("down")

    with pytest.raises(RerankerUnavailable):
        CrossEncoderReranker(scorer=boom).rerank("q", _results())
