from ai.rag.ingestion.chunker import SimpleChunker


def test_chunker():

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": "A" * 1200,
        "metadata": {}
    }

    chunker = SimpleChunker(
        chunk_size=500,
        overlap=50
    )

    chunks = chunker.chunk(document)

    assert len(chunks) > 1

    assert chunks[0]["document_id"] == "test_001"

    assert chunks[0]["document_version"] == "1"

    assert chunks[0]["chunk_id"] == "test_001_chunk_0"