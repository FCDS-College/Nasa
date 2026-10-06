from ai.rag.embeddings.embedding_service import (
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

def test_fake_embedding_service(fake_embedding_service):

    embedding = fake_embedding_service.embed_text(
        "Microgravity affects flames."
    )

    assert embedding is not None
    assert len(embedding) == 8