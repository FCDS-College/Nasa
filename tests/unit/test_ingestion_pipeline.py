from ai.rag.ingestion.pipeline import IngestionPipeline


def test_ingestion_pipeline():

    pipeline = IngestionPipeline()

    result = pipeline.process_document(
        document_id="test_001",
        title="Test Combustion Document",
        source="test_source",
        source_type="test",
        text="Microgravity combustion experiment. " * 100,
        version="1",
        metadata={
            "category": "test"
        }
    )

    document = result["document"]
    chunks = result["chunks"]

    # Check document
    assert document["document_id"] == "test_001"
    assert document["version"] == "1"

    # Check chunks
    assert len(chunks) > 1

    for chunk in chunks:
        assert "chunk_id" in chunk
        assert chunk["document_id"] == "test_001"
        assert chunk["document_version"] == "1"
        assert "text" in chunk
        assert "metadata" in chunk