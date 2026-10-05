from src.citations.citation_manager import CitationManager


def test_citation_manager():

    context_result = {
        "context": (
            "[chunk_1]\n"
            "Microgravity affects flame behavior.\n\n"
            "[chunk_2]\n"
            "Buoyancy is reduced in microgravity."
        ),

        "sources": [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_001",
                "document_version": "1",
                "text": "Microgravity affects flame behavior.",
                "metadata": {
                    "source_type": "NASA"
                }
            },
            {
                "chunk_id": "chunk_2",
                "document_id": "doc_001",
                "document_version": "1",
                "text": "Buoyancy is reduced in microgravity.",
                "metadata": {
                    "source_type": "NASA"
                }
            }
        ]
    }

    citation_manager = CitationManager()

    result = citation_manager.attach_citations(
        context_result
    )

    # -------------------------
    # Check main fields
    # -------------------------

    assert "context" in result
    assert "sources" in result
    assert "citations" in result

    # -------------------------
    # Check number of citations
    # -------------------------

    assert len(result["citations"]) == 2

    # -------------------------
    # Check first citation
    # -------------------------

    citation = result["citations"][0]

    assert citation["citation_id"] == "chunk_1"

    assert citation["chunk_id"] == "chunk_1"

    assert citation["document_id"] == "doc_001"

    assert citation["document_version"] == "1"

    assert citation["metadata"]["source_type"] == "NASA"

    # -------------------------
    # Print citations
    # -------------------------

    print("\nCitations:")

    for citation in result["citations"]:

        print(
            citation["citation_id"],
            "→",
            citation["document_id"],
            "version",
            citation["document_version"]
        )