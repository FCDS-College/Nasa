import pytest

from ai.rag.cache.cag import InMemoryCacheService
from ai.rag.generation.composer import GroundedAnswerComposer
from ai.rag.generation.providers import ExtractiveLLMProvider
from ai.rag.memory.session_mag import InMemorySessionMemory
from ai.rag.reranking.cross_encoder import CrossEncoderReranker
from ai.rag.service import FlameRAGService
from ai.rag.ingestion.chunker import SimpleChunker
from ai.rag.retrieval.keyword_search import KeywordSearchService
from ai.rag.retrieval.rag_retrieval_pipeline import RAGRetrievalPipeline
from ai.rag.retrieval.vector_search import VectorSearchService


@pytest.fixture
def world(fake_embedding_service):
    document = {
        "document_id": "doc_001",
        "version": "v1",
        "text": (
            "Microgravity affects flame behavior. Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. Combustion experiments study flame behavior. "
        ) * 6,
        "metadata": {"environment": "microgravity", "domain": "combustion"},
    }
    chunks = SimpleChunker(chunk_size=200, overlap=30).chunk(document)
    vs = VectorSearchService()
    vs.add_documents(chunks, fake_embedding_service.embed_batch([c["text"] for c in chunks]))
    pipeline = RAGRetrievalPipeline(vs, KeywordSearchService(), fake_embedding_service)
    return pipeline, chunks


def make_service(world, fake_embedding_service, **over):
    pipeline, chunks = world
    kwargs = dict(
        retrieval_pipeline=pipeline,
        composer=GroundedAnswerComposer(ExtractiveLLMProvider()),
        corpus_version="corpus-1",
        embedding_model="fake-embedder",
        cache=InMemoryCacheService(),
        memory=InMemorySessionMemory(),
        reranker=CrossEncoderReranker(scorer=lambda pairs: [0.9 for _ in pairs]),
    )
    kwargs.update(over)
    return FlameRAGService(**kwargs), chunks


Q = "How does microgravity affect flames?"


def test_end_to_end_cited_answer_and_versions(world, fake_embedding_service):
    svc, chunks = make_service(world, fake_embedding_service)
    r = svc.answer(Q, chunks)
    assert r.status == "answered" and r.cache_hit is False
    assert r.answer.citations[0]["document_version"] == "v1"
    assert r.original_query == Q and r.rewritten_query
    assert {"embedding_model", "chunker", "reranker", "corpus_version", "prompt", "llm"} <= set(r.versions)


def test_second_call_is_a_cache_hit_and_corpus_publish_invalidates(world, fake_embedding_service):
    svc, chunks = make_service(world, fake_embedding_service)
    svc.answer(Q, chunks)
    assert svc.answer(Q, chunks).cache_hit is True
    assert svc.cache.invalidate_corpus("corpus-2") == 1
    assert svc.answer(Q, chunks).cache_hit is False


def test_no_matching_evidence_abstains(world, fake_embedding_service):
    svc, chunks = make_service(world, fake_embedding_service)
    r = svc.answer(Q, chunks, filters={"domain": "nonexistent"})
    assert r.status == "insufficient_evidence" and r.answer.claims == []


def test_reranker_down_returns_error_not_uncited_answer(world, fake_embedding_service):
    def boom(pairs):
        raise RuntimeError("model server down")

    svc, chunks = make_service(world, fake_embedding_service, reranker=CrossEncoderReranker(scorer=boom))
    r = svc.answer(Q, chunks)
    assert r.status == "retrieval_unavailable" and r.answer is None and "reranker" in r.error


def test_memory_is_disclosed_and_bypasses_cache(world, fake_embedding_service):
    svc, chunks = make_service(world, fake_embedding_service)
    svc.memory.add_text("alice", "conv_1", "I study microgravity flame behavior")
    r1 = svc.answer(Q, chunks, user_id="alice", conversation_id="conv_1")
    r2 = svc.answer(Q, chunks, user_id="alice", conversation_id="conv_1")
    assert r1.memory_used and r2.cache_hit is False and len(svc.cache) == 0
    # another user does not see alice's memory
    r3 = svc.answer(Q, chunks, user_id="bob", conversation_id="conv_1")
    assert r3.memory_used == []


def test_empty_question_raises(world, fake_embedding_service):
    svc, chunks = make_service(world, fake_embedding_service)
    with pytest.raises(ValueError):
        svc.answer("   ", chunks)
