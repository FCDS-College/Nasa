from ai.rag.ingestion.chunker import SimpleChunker
from ai.rag.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)
from ai.rag.retrieval.vector_search import VectorSearchService


def test_vector_search():

    # -------------------------
    # 1. Create test document
    # -------------------------

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
        ) * 20,
        "metadata": {}
    }

    # -------------------------
    # 2. Chunk document
    # -------------------------

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    # -------------------------
    # 3. Create embeddings
    # -------------------------

    embedding_service = SentenceTransformerEmbeddingService()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_service.embed_batch(texts)

    # -------------------------
    # 4. Create vector search
    # -------------------------

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    # -------------------------
    # 5. Embed query
    # -------------------------

    query = "How does microgravity affect flames?"

    query_embedding = embedding_service.embed_text(query)

    # -------------------------
    # 6. Search
    # -------------------------

    results = vector_search.search(
        query_embedding,
        top_k=3
    )

    # -------------------------
    # 7. Check results
    # -------------------------

    assert len(results) == 3

    for result in results:

        assert "chunk" in result
        assert "score" in result

        print("\nScore:", result["score"])
        print("Chunk:", result["chunk"]["chunk_id"])
        print("Text:", result["chunk"]["text"][:100])