from ai.rag.context.context_builder import ContextBuilder


def test_context_builder():

    results = [
        {
            "chunk": {
                "chunk_id": "chunk_1",
                "document_id": "doc_001",
                "document_version": "1",
                "text": "Microgravity affects flame behavior.",
                "metadata": {
                    "source_type": "NASA"
                }
            },
            "rerank_score": 0.90
        },
        {
            "chunk": {
                "chunk_id": "chunk_2",
                "document_id": "doc_001",
                "document_version": "1",
                "text": "Buoyancy is reduced in microgravity.",
                "metadata": {
                    "source_type": "NASA"
                }
            },
            "rerank_score": 0.85
        },
        {
            "chunk": {
                "chunk_id": "chunk_1",
                "document_id": "doc_001",
                "document_version": "1",
                "text": "Microgravity affects flame behavior.",
                "metadata": {
                    "source_type": "NASA"
                }
            },
            "rerank_score": 0.80
        }
    ]

    context_builder = ContextBuilder(
        max_chunks=5,
        max_characters=1000
    )

    result = context_builder.build(results)

    # -------------------------
    # Check context
    # -------------------------

    assert "context" in result
    assert "sources" in result

    # -------------------------
    # Check duplicate removal
    # -------------------------

    assert len(result["sources"]) == 2

    # -------------------------
    # Check provenance
    # -------------------------

    first_source = result["sources"][0]

    assert first_source["chunk_id"] == "chunk_1"
    assert first_source["document_id"] == "doc_001"
    assert first_source["document_version"] == "1"

    assert "metadata" in first_source

    # -------------------------
    # Check text
    # -------------------------

    assert (
        "Microgravity affects flame behavior."
        in result["context"]
    )

    assert (
        "Buoyancy is reduced in microgravity."
        in result["context"]
    )

    # -------------------------
    # Print result
    # -------------------------

    print("\nContext:")
    print(result["context"])

    print("\nSources:")

    for source in result["sources"]:
        print(
            source["chunk_id"],
            "→",
            source["document_id"],
            "version",
            source["document_version"]
        )