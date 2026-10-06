class KeywordSearchService:

    def search(self, chunks, query, top_k=5):
        """
        Search chunks based on keyword overlap.

        Parameters
        ----------
        chunks : list[dict]
            Available chunks.

        query : str
            User search query.

        top_k : int
            Number of results to return.

        Returns
        -------
        list[dict]
            Ranked chunks with keyword scores.
        """

        query_words = set(query.lower().split())

        results = []

        for chunk in chunks:

            text = chunk["text"].lower()

            score = sum(
                1
                for word in query_words
                if word in text
            )

            if score > 0:
                results.append({
                    "chunk": chunk,
                    "score": float(score)
                })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results[:top_k]