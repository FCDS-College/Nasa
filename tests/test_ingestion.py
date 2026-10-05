from src.ingestion.document import create_document
from src.ingestion.chunker import SimpleChunker


def test_document_to_chunks():

    document = create_document(
        document_id="test_001",
        title="Test Combustion Document",
        source="test_source",
        source_type="test",
        text="Microgravity combustion experiment. " * 100,
        metadata={
            "category": "test"
        }
    )

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    assert len(chunks) > 1

    for chunk in chunks:

        assert "chunk_id" in chunk
        assert "document_id" in chunk
        assert "document_version" in chunk
        assert "text" in chunk
        assert "metadata" in chunk