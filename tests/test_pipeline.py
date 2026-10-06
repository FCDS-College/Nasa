from src.ingestion.pipeline import IngestionPipeline


pipeline = IngestionPipeline()

result = pipeline.process_document(
    document_id="test_001",
    title="Microgravity Combustion Example",
    source="test_source",
    source_type="test",
    text=(
        "Microgravity affects buoyancy-driven flow around flames. "
        "This is test data for the ingestion pipeline. "
    ) * 100,
    metadata={}
)

print("Document:")
print(result["document"])

print("\nNumber of chunks:")
print(len(result["chunks"]))

print("\nFirst chunk:")
print(result["chunks"][0])