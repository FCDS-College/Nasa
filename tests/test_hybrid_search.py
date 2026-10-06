from src.ingestion.chunker import SimpleChunker
from src.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)
from src.retrieval.vector_search import VectorSearchService
from src.retrieval.keyword_search import KeywordSearchService
from src.retrieval.hybrid_search import HybridSearchService


def test_hybrid_search():

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
            "Combustion experiments study flame behavior. "
        ) * 10,
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
    # 4. Create Vector Search
    # -------------------------

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    # -------------------------
    # 5. Create Keyword Search
    # -------------------------

    keyword_search = KeywordSearchService()

    # -------------------------
    # 6. Create Hybrid Search
    # -------------------------

    hybrid_search = HybridSearchService(
        vector_search=vector_search,
        keyword_search=keyword_search
    )

    # -------------------------
    # 7. Query
    # -------------------------

    query = "How does microgravity affect flames?"

    query_embedding = embedding_service.embed_text(
        query
    )

    # -------------------------
    # 8. Hybrid Search
    # -------------------------

    results = hybrid_search.search(
        chunks=chunks,
        query=query,
        query_embedding=query_embedding,
        top_k=3
    )

    # -------------------------
    # 9. Check results
    # -------------------------

    assert len(results) == 3

    for result in results:

        assert "chunk" in result
        assert "vector_score" in result
        assert "keyword_score" in result
        assert "hybrid_score" in result

        print("\nChunk:", result["chunk"]["chunk_id"])
        print("Vector score:", result["vector_score"])
        print("Keyword score:", result["keyword_score"])
        print("Hybrid score:", result["hybrid_score"])
        print("Text:", result["chunk"]["text"][:100])