class Reranker:

    def rerank(self, query, results, top_k=5):
        """
        Rerank retrieved results based on query-chunk relevance.

        Parameters
        ----------
        query : str
            User query.

        results : list[dict]
            Results returned by the retrieval layer.

        top_k : int
            Number of final results.

        Returns
        -------
        list[dict]
            Reranked results.
        """

        query_words = set(query.lower().split())

        reranked_results = []

        for result in results:

            chunk = result["chunk"]

            text = chunk["text"].lower()

            # Count query words appearing in the chunk
            matching_words = sum(
                1
                for word in query_words
                if word in text
            )

            # Normalize based on number of query words
            if len(query_words) > 0:
                keyword_relevance = (
                    matching_words / len(query_words)
                )
            else:
                keyword_relevance = 0.0

            # Use the existing hybrid score
            hybrid_score = result.get(
                "hybrid_score",
                0.0
            )

            # Combine retrieval score with
            # direct query-chunk relevance
            rerank_score = (
                0.7 * hybrid_score
                +
                0.3 * keyword_relevance
            )

            reranked_results.append({
                "chunk": chunk,
                "retrieval_score": hybrid_score,
                "keyword_relevance": float(
                    keyword_relevance
                ),
                "rerank_score": float(
                    rerank_score
                )
            })

        # Sort from highest relevance to lowest
        reranked_results.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        return reranked_results[:top_k]