from abc import ABC, abstractmethod




class EmbeddingService(ABC):

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

    def __init__(
        self,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    ):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_text(self, text):

        embedding = self.model.encode(
            text,
            convert_to_numpy=True
        )

        return embedding

    def embed_batch(self, texts):

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True
        )

        return embeddings