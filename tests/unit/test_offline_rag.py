"""Disconnected run: the whole answer flow must work with no network at all."""
import socket

import pytest

from ai.rag.cache.cag import InMemoryCacheService
from ai.rag.generation.composer import GroundedAnswerComposer
from ai.rag.generation.providers import ExtractiveLLMProvider
from ai.rag.ingestion.chunker import SimpleChunker
from ai.rag.reranking.cross_encoder import CrossEncoderReranker
from ai.rag.retrieval.keyword_search import KeywordSearchService
from ai.rag.retrieval.rag_retrieval_pipeline import RAGRetrievalPipeline
from ai.rag.retrieval.vector_search import VectorSearchService
from ai.rag.service import FlameRAGService


@pytest.fixture
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted during an offline run")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def test_disconnected_run_answers_with_verifiable_evidence(no_network, fake_embedding_service):
    document = {
        "document_id": "doc_local_001",
        "version": "v1",
        "text": (
            "Microgravity affects flame behavior. Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
        ) * 8,
        "metadata": {"environment": "microgravity", "domain": "combustion"},
    }
    chunks = SimpleChunker(chunk_size=200, overlap=30).chunk(document)
    vs = VectorSearchService()
    vs.add_documents(chunks, fake_embedding_service.embed_batch([c["text"] for c in chunks]))
    service = FlameRAGService(
        RAGRetrievalPipeline(vs, KeywordSearchService(), fake_embedding_service),
        GroundedAnswerComposer(ExtractiveLLMProvider()),
        corpus_version="local-corpus-1",
        embedding_model="fake-embedder",
        cache=InMemoryCacheService(),
        reranker=CrossEncoderReranker(scorer=lambda pairs: [0.9 for _ in pairs]),
    )

    response = service.answer("How does microgravity affect flames?", chunks)

    assert response.status == "answered"
    cited = {c["chunk_id"] for c in response.answer.citations}
    stored = {c["chunk_id"] for c in chunks}
    assert cited and cited <= stored  # every citation resolves to a locally indexed chunk
    assert all(c["document_version"] == "v1" for c in response.answer.citations)
