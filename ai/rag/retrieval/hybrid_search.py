class HybridSearchService:

    """Combines vector and keyword scores over the given chunks: hybrid = vector_weight * vector_score + keyword_weight * (keyword_score / max keyword score), weights 0.7 and 0.3 by default.

    Note: every given chunk gets a score, so up to top_k chunks are returned even when their hybrid score is 0."""

    def __init__(
        self,
        vector_search,
        keyword_search,
        vector_weight=0.7,
        keyword_weight=0.3
    ):
        self.vector_search = vector_search
        self.keyword_search = keyword_search

        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def search(
        self,
        chunks,
        query,
        query_embedding,
        top_k=5
    ):
        """
        Combine vector and keyword search results.

        Parameters
        ----------
        chunks : list[dict]
            Available chunks.

        query : str
            User query.

        query_embedding : array
            Embedding of the user query.

        top_k : int
            Number of final results.

        Returns
        -------
        list[dict]
            Hybrid-ranked results.
        """

        # -------------------------
        # 1. Vector Search
        # -------------------------

        vector_results = self.vector_search.search(
        query_embedding,
        top_k=len(chunks),
        chunks=chunks
)

        # -------------------------
        # 2. Keyword Search
        # -------------------------

        keyword_results = self.keyword_search.search(
            chunks,
            query,
            top_k=len(chunks)
        )

        # -------------------------
        # 3. Store scores by chunk
        # -------------------------

        vector_scores = {}

        for result in vector_results:

            chunk_id = result["chunk"]["chunk_id"]

            vector_scores[chunk_id] = result["score"]

        keyword_scores = {}

        for result in keyword_results:

            chunk_id = result["chunk"]["chunk_id"]

            keyword_scores[chunk_id] = result["score"]

        # -------------------------
        # 4. Normalize keyword scores
        # -------------------------

        max_keyword_score = max(
            keyword_scores.values(),
            default=0
        )

        # -------------------------
        # 5. Calculate hybrid score
        # -------------------------

        hybrid_results = []

        for chunk in chunks:

            chunk_id = chunk["chunk_id"]

            vector_score = vector_scores.get(
                chunk_id,
                0.0
            )

            keyword_score = keyword_scores.get(
                chunk_id,
                0.0
            )

            if max_keyword_score > 0:
                normalized_keyword_score = (
                    keyword_score / max_keyword_score
                )
            else:
                normalized_keyword_score = 0.0

            hybrid_score = (
                self.vector_weight * vector_score
                +
                self.keyword_weight * normalized_keyword_score
            )

            hybrid_results.append({
                "chunk": chunk,
                "vector_score": float(vector_score),
                "keyword_score": float(
                    normalized_keyword_score
                ),
                "hybrid_score": float(hybrid_score)
            })

        # -------------------------
        # 6. Rank results
        # -------------------------

        hybrid_results.sort(
            key=lambda x: x["hybrid_score"],
            reverse=True
        )

        return hybrid_results[:top_k]