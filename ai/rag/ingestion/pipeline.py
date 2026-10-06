from ai.rag.ingestion.document import create_document
from ai.rag.ingestion.chunker import SimpleChunker


class IngestionPipeline:

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