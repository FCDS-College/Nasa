import pytest

from pydantic import ValidationError

from ai.rag.dto import (
    Locator,
    RetrievalRequest,
    RetrievedChunk,
    EvidenceBundle
)


def test_retrieval_request():

    request = RetrievalRequest(
        query="How does microgravity affect flames?",
        top_k=5,
        filters={
            "domain": "combustion"
        }
    )

    assert request.query == "How does microgravity affect flames?"
    assert request.top_k == 5
    assert request.filters["domain"] == "combustion"


def test_retrieved_chunk():

    chunk = RetrievedChunk(
        chunk_id="ntrs_001_chunk_0",
        document_id="ntrs_001",
        document_version="1",
        text="Microgravity affects flame behavior.",
        score=0.91,
        locator=Locator(
            page=3,
            section="Introduction"
        ),
        metadata={
            "domain": "combustion"
        }
    )

    assert chunk.chunk_id == "ntrs_001_chunk_0"
    assert chunk.document_version == "1"
    assert chunk.score == 0.91
    assert chunk.locator.page == 3
    assert chunk.locator.section == "Introduction"


def test_evidence_bundle():

    chunk = RetrievedChunk(
        chunk_id="ntrs_001_chunk_0",
        document_id="ntrs_001",
        document_version="1",
        text="Microgravity affects flame behavior.",
        score=0.91
    )

    bundle = EvidenceBundle(
        query="How does microgravity affect flames?",
        evidence=[chunk]
    )

    assert bundle.query == "How does microgravity affect flames?"
    assert len(bundle.evidence) == 1
    assert bundle.status == "ok"


def test_retrieval_request_rejects_invalid_top_k():

    with pytest.raises(ValidationError):

        RetrievalRequest(
            query="test",
            top_k=0
        )