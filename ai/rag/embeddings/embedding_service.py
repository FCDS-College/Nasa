from abc import ABC, abstractmethod


from abc import ABC, abstractmethod


class EmbeddingService(ABC):

    """Abstract interface that turns text into embedding vectors."""
    @abstractmethod
    def embed_text(self, text):
        """
        Convert a single text into an embedding vector.
        """
        pass

    @abstractmethod
    def embed_batch(self, texts):
        """
        Convert multiple texts into embedding vectors.
        """
        pass


class SentenceTransformerEmbeddingService(EmbeddingService):

    """Embeddings from a sentence-transformers model (default sentence-transformers/all-MiniLM-L6-v2).

    Requires the sentence-transformers package. For offline use the model files must already be available locally. Model version and dimension are not recorded by this class."""

    def __init__(
        self,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    ):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_text(self, text):

        """Embed one text.

        Args:
            text: the text to embed.

        Returns:
            A numpy vector."""

        embedding = self.model.encode(
            text,
            convert_to_numpy=True
        )

        return embedding

    def embed_batch(self, texts):

        """Embed several texts.

        Args:
            texts: list of strings.

        Returns:
            A numpy array with one row per text."""

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True
        )

        return embeddings