from src.ingestion.chunker import SimpleChunker
from src.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)
from src.retrieval.vector_search import VectorSearchService
from src.retrieval.keyword_search import KeywordSearchService
from src.retrieval.rag_retrieval_pipeline import (
    RAGRetrievalPipeline
)


def test_rag_retrieval_pipeline():

    # -------------------------
    # 1. Test document
    # -------------------------

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
            "Combustion experiments study flame behavior. "
            "Earth gravity produces stronger buoyancy driven flow. "
        ) * 10,
        "metadata": {
            "environment": "microgravity",
            "source_type": "test"
        }
    }

    # -------------------------
    # 2. Chunking
    # -------------------------

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    # -------------------------
    # 3. Embeddings
    # -------------------------

    embedding_service = SentenceTransformerEmbeddingService()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_service.embed_batch(
        texts
    )

    # -------------------------
    # 4. Vector search
    # -------------------------

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    # -------------------------
    # 5. Keyword search
    # -------------------------

    keyword_search = KeywordSearchService()

    # -------------------------
    # 6. RAG retrieval pipeline
    # -------------------------

    pipeline = RAGRetrievalPipeline(
        vector_search=vector_search,
        keyword_search=keyword_search,
        embedding_service=embedding_service
    )

    # -------------------------
    # 7. Query
    # -------------------------

    query = "How does microgravity affect flames?"

    # -------------------------
    # 8. Retrieval
    # -------------------------

    result = pipeline.retrieve(
        query=query,
        chunks=chunks,
        metadata_filters={
            "environment": "microgravity"
        },
        top_k=3
    )

    # -------------------------
    # 9. Assertions
    # -------------------------

    assert result["query"] == query

    assert "context" in result
    assert "sources" in result
    assert "citations" in result
    assert "results" in result

    assert len(result["results"]) > 0
    assert len(result["sources"]) > 0
    assert len(result["citations"]) > 0

    # Check citation information

    citation = result["citations"][0]

    assert "citation_id" in citation
    assert "chunk_id" in citation
    assert "document_id" in citation
    assert "document_version" in citation

    # -------------------------
    # 10. Print result
    # -------------------------

    print("\n==============================")
    print("QUERY")
    print("==============================")
    print(query)

    print("\n==============================")
    print("CONTEXT")
    print("==============================")
    print(result["context"])

    print("\n==============================")
    print("CITATIONS")
    print("==============================")

    for citation in result["citations"]:

        print(
            citation["citation_id"],
            "→",
            citation["document_id"],
            "version",
            citation["document_version"]
        )