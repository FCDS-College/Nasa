from pathlib import Path

from src.ingestion.document import create_document
from src.ingestion.chunker import SimpleChunker
from src.ingestion.pdf_loader import PDFDocumentLoader


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


def test_pdf_loader_creates_page_level_documents():

    pdf_path = Path(
        "data/raw/20000034017.pdf"
    )

    assert pdf_path.exists()

    loader = PDFDocumentLoader()

    documents = loader.load(pdf_path)

    assert len(documents) == 20

    first_document = documents[0]

    assert (
        first_document["document_id"]
        == "20000034017_page_1"
    )

    assert first_document["source_type"] == "pdf"

    assert (
        first_document["metadata"]["domain"]
        == "combustion"
    )

    assert (
        first_document["metadata"]["locator"]["page"]
        == 1
    )

    assert first_document["text"]
