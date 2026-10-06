id="s5wq4n"
from ai.rag.ingestion.chunker import SimpleChunker

from ai.rag.retrieval.vector_search import VectorSearchService
from ai.rag.retrieval.keyword_search import KeywordSearchService
from ai.rag.retrieval.rag_retrieval_pipeline import (
    RAGRetrievalPipeline
)


def test_rag_retrieval_pipeline(
    fake_embedding_service
):

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
            "Combustion experiments study flame behavior."
        ) * 10,
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

    query = "How does microgravity affect flames?"

    result = pipeline.retrieve(
        query=query,
        chunks=chunks,
        metadata_filters={
            "environment": "microgravity"
        },
        top_k=3
    )

    assert result["query"] == query

    assert "context" in result
    assert "sources" in result
    assert "citations" in result
    assert "results" in result

    assert len(result["results"]) > 0
    assert len(result["sources"]) > 0
    assert len(result["citations"]) > 0

    for citation in result["citations"]:

        assert "citation_id" in citation
        assert "chunk_id" in citation
        assert "document_id" in citation
        assert "document_version" in citation


def test_rag_pipeline_returns_evidence_bundle(
    fake_embedding_service
):
    from ai.rag.dto import EvidenceBundle
    from ai.rag.retrieval.vector_search import VectorSearchService
    from ai.rag.retrieval.keyword_search import KeywordSearchService
    from ai.rag.retrieval.rag_retrieval_pipeline import (
        RAGRetrievalPipeline
    )

    chunks = [
        {
            "chunk_id": "combustion_chunk_0",
            "document_id": "combustion_doc",
            "document_version": "1",
            "text": (
                "Microgravity changes flame behavior "
                "and combustion characteristics."
            ),
            "chunk_index": 0,
            "metadata": {
                "domain": "combustion"
            }
        }
    ]

    vector_search = VectorSearchService(
        min_score=0.0
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
        query="How does microgravity affect flame behavior?",
        chunks=chunks
    )

    evidence = EvidenceBundle(
        query=result["query"],
        status=result["status"]
    )

    assert isinstance(
        evidence,
        EvidenceBundle
    )

    assert evidence.status == "ok"


def test_rag_pipeline_preserves_locator_in_evidence_and_citations(
    fake_embedding_service
):
    from ai.rag.retrieval.vector_search import VectorSearchService
    from ai.rag.retrieval.keyword_search import KeywordSearchService
    from ai.rag.retrieval.rag_retrieval_pipeline import (
        RAGRetrievalPipeline
    )

    chunks = [
        {
            "chunk_id": "ntrs_001_chunk_0",
            "document_id": "ntrs_001",
            "document_version": "1",
            "text": "Microgravity affects flame behavior.",
            "metadata": {
                "domain": "combustion",
                "locator": {
                    "page": 7,
                    "section": "Flame Behavior"
                }
            }
        }
    ]

    embeddings = fake_embedding_service.embed_batch(
        [chunk["text"] for chunk in chunks]
    )

    vector_search = VectorSearchService(
        min_score=0.0
    )

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

    result = pipeline.retrieve(
        query="microgravity flame behavior",
        chunks=chunks,
        top_k=1
    )

    assert result.status == "ok"
    assert len(result.evidence) == 1

    evidence = result.evidence[0]

    assert evidence.locator is not None
    assert evidence.locator.page == 7
    assert evidence.locator.section == "Flame Behavior"

    assert len(result.citations) == 1

    citation = result.citations[0]

    assert "locator" in citation
    assert citation["locator"]["page"] == 7
    assert citation["locator"]["section"] == "Flame Behavior"
