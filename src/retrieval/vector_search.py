import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class VectorSearchService:

    def __init__(self, min_score=0.7):
      self.chunks = []
      self.embeddings = []
      self.min_score = min_score

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

    def search(
        self,
        query_embedding,
        top_k=5,
        chunks=None
    ):
        """
        Search for the most semantically similar chunks.

        If chunks are provided, search only within those chunks.
        Otherwise, search across all stored chunks.
        """

        if not self.chunks:
            return []

        # Search within the requested subset
        if chunks is not None:

            chunk_ids = {
                chunk["chunk_id"]
                for chunk in chunks
            }

            selected_indices = [
                index
                for index, chunk in enumerate(self.chunks)
                if chunk["chunk_id"] in chunk_ids
            ]

        else:

            selected_indices = list(
                range(len(self.chunks))
            )

        if not selected_indices:
            return []

        embeddings_matrix = np.array([
            self.embeddings[index]
            for index in selected_indices
        ])

        query_vector = np.array(
            query_embedding
        ).reshape(1, -1)

        scores = cosine_similarity(
            query_vector,
            embeddings_matrix
        )[0]

        ranked_positions = np.argsort(scores)[::-1]

        results = []

        for position in ranked_positions[:top_k]:

             score = float(scores[position])

             if score < self.min_score:
               continue

             original_index = selected_indices[position]

             result = {
               "chunk": self.chunks[original_index],
                "score": score
              }

             results.append(result)

        return results