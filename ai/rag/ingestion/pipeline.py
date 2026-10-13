from ai.rag.ingestion.document import create_document
from ai.rag.ingestion.chunker import SimpleChunker


class IngestionPipeline:

    """Creates a document and splits it into chunks (default chunker: SimpleChunker)."""
    def __init__(self, chunker=None):
        self.chunker = chunker or SimpleChunker()

    def process_document(
        self,
        document_id,
        title,
        source,
        source_type,
        text,
        version="1",
        metadata=None,
    ):
        # Step 1: Create internal document representation
        """Create a document and chunk it.

        Args:
            document_id, title, source, source_type, text: document fields.
            version: document version string (default "1").
            metadata: optional metadata dict.

        Returns:
            {"document": dict, "chunks": list of chunk dicts}."""

        document = create_document(
            document_id=document_id,
            title=title,
            source=source,
            source_type=source_type,
            text=text,
            version=version,
            metadata=metadata,
        )

        # Step 2: Split document into chunks
        chunks = self.chunker.chunk(document)

        return {
            "document": document,
            "chunks": chunks,
        }