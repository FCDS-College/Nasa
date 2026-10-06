id="n8k1df"
from ai.rag.ingestion.chunker import SimpleChunker

from ai.rag.retrieval.vector_search import VectorSearchService
from ai.rag.retrieval.keyword_search import KeywordSearchService
from ai.rag.retrieval.rag_retrieval_pipeline import (
    RAGRetrievalPipeline
)


def build_pipeline(fake_embedding_service):

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
            "Combustion experiments study flame behavior."
        ),
        "metadata": {
            "environment": "microgravity",
            "source_type": "test",
            "domain": "combustion"
        }
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

    pipeline = RAGRetrievalPipeline(
        vector_search=vector_search,
        keyword_search=keyword_search,
        embedding_service=fake_embedding_service
    )

    return pipeline, chunks


def test_no_relevant_document(fake_embedding_service):

    pipeline, chunks = build_pipeline(
        fake_embedding_service
    )

    result = pipeline.retrieve(
        query=(
            "What is the chemical composition "
            "of Saturn?"
        ),
        chunks=chunks,
        metadata_filters={
            "environment": "microgravity"
        },
        top_k=3
    )

    assert "context" in result
    assert "citations" in result


def test_metadata_filter_no_match(
    fake_embedding_service
):

    pipeline, chunks = build_pipeline(
        fake_embedding_service
    )

    result = pipeline.retrieve(
        query="How does microgravity affect flames?",
        chunks=chunks,
        metadata_filters={
            "environment": "deep_space"
        },
        top_k=3
    )

    assert result["context"] == ""
    assert result["sources"] == []
    assert result["citations"] == []


def test_insufficient_context(
    fake_embedding_service
):

    pipeline, chunks = build_pipeline(
        fake_embedding_service
    )

    result = pipeline.retrieve(
        query="How does microgravity affect flames?",
        chunks=chunks,
        metadata_filters={
            "environment": "microgravity"
        },
        top_k=1
    )

    assert "context" in result
    assert len(result["sources"]) <= 1


def test_combustion_query_never_returns_dsi(
    fake_embedding_service
):

    pipeline, chunks = build_pipeline(
        fake_embedding_service
    )

    # Add a DSI chunk to the same retrieval corpus.
    dsi_chunk = {
        "chunk_id": "dsi_001_chunk_0",
        "document_id": "dsi_001",
        "document_version": "1",
        "text": (
            "DSI is a data science infrastructure "
            "unrelated to combustion."
        ),
        "metadata": {
            "domain": "DSI"
        }
    }

    chunks_with_dsi = chunks + [dsi_chunk]

    # The query is explicitly about combustion.
    result = pipeline.retrieve(
        query=(
            "How does microgravity affect "
            "combustion flames?"
        ),
        chunks=chunks_with_dsi,
        top_k=5
    )

    retrieved_ids = {
        item["chunk"]["chunk_id"]
        for item in result["results"]
    }

    assert "dsi_001_chunk_0" not in retrieved_ids

def test_no_relevant_document_returns_insufficient_evidence(
    fake_embedding_service
):
    from ai.rag.retrieval.vector_search import VectorSearchService
    from ai.rag.retrieval.keyword_search import KeywordSearchService
    from ai.rag.retrieval.rag_retrieval_pipeline import RAGRetrievalPipeline

    chunks = [
        {
            "chunk_id": "mars_chunk_0",
            "document_id": "mars_doc",
            "document_version": "1",
            "text": "Mars has a thin atmosphere composed mostly of carbon dioxide.",
            "chunk_index": 0,
            "metadata": {
                "domain": "planetary_science"
            }
        }
    ]

    vector_search = VectorSearchService(
        min_score=0.99
    )

    embedding = fake_embedding_service.embed_text(
        chunks[0]["text"]
    )

    vector_search.add_documents(
        chunks,
        [embedding]
    )

    pipeline = RAGRetrievalPipeline(
        vector_search=vector_search,
        keyword_search=KeywordSearchService(),
        embedding_service=fake_embedding_service
    )

    result = pipeline.retrieve(
        query="How does microgravity affect combustion?",
        chunks=chunks
    )

    assert result["status"] == "insufficient_evidence"
    assert result["context"] == ""
    assert result["sources"] == []
    assert result["citations"] == []
    assert result["results"] == []
