import numpy as np
import pytest


class FakeEmbeddingService:

    def __init__(self, dimension=8):
        self.dimension = dimension

    def _embed(self, text):
        """
        Create a deterministic fake embedding.

        This is only for tests.
        It does not represent real semantic embeddings.
        """

        vector = np.zeros(self.dimension)

        for index, character in enumerate(text.lower()):
            vector[index % self.dimension] += ord(character)

        norm = np.linalg.norm(vector)

        if norm > 0:
            vector = vector / norm

        return vector

    def embed_text(self, text):
        return self._embed(text)

    def embed_batch(self, texts):
        return np.array([
            self._embed(text)
            for text in texts
        ])


@pytest.fixture
def fake_embedding_service():
    return FakeEmbeddingService()
