from evaluation.metrics import (
    recall_at_k,
    reciprocal_rank,
    citation_coverage
)


def test_recall_at_k():

    retrieved = [
        {
            "chunk": {
                "chunk_id": "chunk_1"
            }
        },
        {
            "chunk": {
                "chunk_id": "chunk_2"
            }
        },
        {
            "chunk": {
                "chunk_id": "chunk_3"
            }
        }
    ]

    relevant = [
        "chunk_1",
        "chunk_3"
    ]

    score = recall_at_k(
        retrieved,
        relevant,
        k=3
    )

    assert score == 1.0


def test_reciprocal_rank():

    retrieved = [
        {
            "chunk": {
                "chunk_id": "chunk_x"
            }
        },
        {
            "chunk": {
                "chunk_id": "chunk_1"
            }
        },
        {
            "chunk": {
                "chunk_id": "chunk_2"
            }
        }
    ]

    relevant = [
        "chunk_1"
    ]

    score = reciprocal_rank(
        retrieved,
        relevant
    )

    assert score == 0.5


def test_citation_coverage():

    citations = [
        {
            "chunk_id": "chunk_1"
        },
        {
            "chunk_id": "chunk_2"
        }
    ]

    relevant = [
        "chunk_1",
        "chunk_2"
    ]

    score = citation_coverage(
        citations,
        relevant
    )

    assert score == 1.0