from ai.rag.reranking.reranker import Reranker


def test_reranker():

    results = [
        {
            "chunk": {
                "chunk_id": "chunk_1",
                "text": (
                    "Microgravity affects flame behavior "
                    "and changes combustion."
                )
            },
            "hybrid_score": 0.80
        },
        {
            "chunk": {
                "chunk_id": "chunk_2",
                "text": (
                    "This document discusses unrelated "
                    "materials and equipment."
                )
            },
            "hybrid_score": 0.85
        },
        {
            "chunk": {
                "chunk_id": "chunk_3",
                "text": (
                    "Microgravity changes the flow around "
                    "flames during combustion experiments."
                )
            },
            "hybrid_score": 0.75
        }
    ]

    reranker = Reranker()

    query = "How does microgravity affect flames?"

    reranked_results = reranker.rerank(
        query=query,
        results=results,
        top_k=3
    )

    # Check number of results

    assert len(reranked_results) == 3

    # Check required fields

    for result in reranked_results:

        assert "chunk" in result
        assert "retrieval_score" in result
        assert "keyword_relevance" in result
        assert "rerank_score" in result

    # Results should be sorted
    # from highest rerank score to lowest

    assert (
        reranked_results[0]["rerank_score"]
        >=
        reranked_results[1]["rerank_score"]
    )

    assert (
        reranked_results[1]["rerank_score"]
        >=
        reranked_results[2]["rerank_score"]
    )

    # Print results

    for result in reranked_results:

        print(
            "\nChunk:",
            result["chunk"]["chunk_id"]
        )

        print(
            "Retrieval score:",
            result["retrieval_score"]
        )

        print(
            "Keyword relevance:",
            result["keyword_relevance"]
        )

        print(
            "Rerank score:",
            result["rerank_score"]
        )

def test_reranker_does_not_recompute_keyword_overlap():
    from ai.rag.reranking.reranker import Reranker

    results = [
        {
            "chunk": {
                "chunk_id": "chunk_1",
                "text": "flame temperature microgravity",
                "metadata": {}
            },
            "hybrid_score": 0.5
        },
        {
            "chunk": {
                "chunk_id": "chunk_2",
                "text": "unrelated content",
                "metadata": {}
            },
            "hybrid_score": 0.5
        }
    ]

    reranker = Reranker()

    reranked = reranker.rerank(
        query="flame temperature",
        results=results,
        top_k=2
    )

    # Both chunks have the same retrieval score.
    # The reranker should not create an additional
    # keyword-overlap advantage for chunk_1.
    assert (
        reranked[0]["rerank_score"]
        == reranked[1]["rerank_score"]
    )
