import re

class KeywordSearchService:

    def search(
        self,
        chunks,
        query,
        top_k=5
    ):
        """
        Search chunks using exact token matching.

        Query words are matched against complete
        words in the chunk text.

        Substring matches are not counted.
        """

        query_words = set(
            re.findall(
                r"\b\w+\b",
                query.lower()
            )
        )

        if not query_words:
            return []

        results = []

        for chunk in chunks:

            text = chunk["text"].lower()

            text_words = set(
                re.findall(
                    r"\b\w+\b",
                    text
                )
            )

            matching_words = (
                query_words.intersection(
                    text_words
                )
            )

            score = len(matching_words)

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
