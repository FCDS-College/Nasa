from src.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)


def test_embedding():

    service = SentenceTransformerEmbeddingService()

    text = (
        "Microgravity affects buoyancy-driven "
        "flow around flames."
    )

    embedding = service.embed_text(text)

    assert embedding is not None
    assert len(embedding) > 0

    print("\nEmbedding dimension:", len(embedding))
    print("First 10 values:", embedding[:10])