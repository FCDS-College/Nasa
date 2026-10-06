from src.ingestion.chunker import SimpleChunker
from src.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)
from src.retrieval.vector_search import VectorSearchService
from src.retrieval.keyword_search import KeywordSearchService
from src.retrieval.rag_retrieval_pipeline import (
    RAGRetrievalPipeline
)


def build_pipeline():

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
            "source_type": "test"
        }
    }

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    embedding_service = SentenceTransformerEmbeddingService()

    embeddings = embedding_service.embed_batch(
        [chunk["text"] for chunk in chunks]
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
        embedding_service=embedding_service
    )

    return pipeline, chunks


def test_no_relevant_document():

    pipeline, chunks = build_pipeline()

    result = pipeline.retrieve(
        query="What is the chemical composition of Saturn?",
        chunks=chunks,
        metadata_filters={
            "environment": "microgravity"
        },
        top_k=3
    )

    assert "context" in result
    assert "citations" in result


def test_metadata_filter_no_match():

    pipeline, chunks = build_pipeline()

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


def test_insufficient_context():

    pipeline, chunks = build_pipeline()

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