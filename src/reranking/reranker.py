class Reranker:

    def rerank(self, query, results, top_k=5):
        """
        Rerank retrieval results using the score produced
        by the retrieval stage.

        Keyword overlap is intentionally not recomputed here.
        It is already represented in the hybrid retrieval score.
        """

        reranked_results = []

        for result in results:

            chunk = result["chunk"]

            hybrid_score = float(
                result.get(
                    "hybrid_score",
                    0.0
                )
            )

            # Keep this field for backward compatibility
            # with the existing pipeline/tests.
            # It is not used to calculate rerank_score.
            keyword_relevance = None

            rerank_score = hybrid_score

            reranked_results.append({
                "chunk": chunk,
                "retrieval_score": hybrid_score,
                "keyword_relevance": keyword_relevance,
                "rerank_score": float(
                    rerank_score
                )
            })

        reranked_results.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        return reranked_results[:top_k]
