from src.ingestion.chunker import SimpleChunker
from src.retrieval.vector_search import VectorSearchService
from src.retrieval.keyword_search import KeywordSearchService
from src.retrieval.hybrid_search import HybridSearchService

def test_hybrid_search(fake_embedding_service):

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
            "Earth gravity produces stronger buoyancy."
        ) * 10,
        "metadata": {}
    }

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    embeddings = fake_embedding_service.embed_batch(
        [
            chunk["text"]
            for chunk in chunks
        ]
    )

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    keyword_search = KeywordSearchService()

    hybrid_search = HybridSearchService(
        vector_search=vector_search,
        keyword_search=keyword_search
    )

    query = "microgravity flame"

    query_embedding = fake_embedding_service.embed_text(
        query
    )

    results = hybrid_search.search(
        chunks=chunks,
        query=query,
        query_embedding=query_embedding,
        top_k=3
    )

    assert len(results) == 3

    for result in results:

        assert "chunk" in result
        assert "vector_score" in result
        assert "keyword_score" in result
        assert "hybrid_score" in result

    assert (
        results[0]["hybrid_score"]
        >= results[-1]["hybrid_score"]
    )
