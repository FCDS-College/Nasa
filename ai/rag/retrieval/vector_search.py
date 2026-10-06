import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class VectorSearchService:

    def __init__(self):
        self.chunks = []
        self.embeddings = []

    def add_documents(self, chunks, embeddings):
        """
        Store chunks and their corresponding embeddings.
        """

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks must match number of embeddings."
            )

        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)

    def search(self, query_embedding, top_k=5):
        """
        Search for the most semantically similar chunks.
        """

        if not self.chunks:
            return []

        embeddings_matrix = np.array(self.embeddings)

        query_vector = np.array(query_embedding).reshape(1, -1)

        scores = cosine_similarity(
            query_vector,
            embeddings_matrix
        )[0]

        ranked_indices = np.argsort(scores)[::-1]

        results = []

        for index in ranked_indices[:top_k]:

            result = {
                "chunk": self.chunks[index],
                "score": float(scores[index])
            }

            results.append(result)

        return results