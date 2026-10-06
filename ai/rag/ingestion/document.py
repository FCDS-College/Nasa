def create_document(
    document_id,
    title,
    source,
    source_type,
    text,
    version="1",
    metadata=None,
):
    """
    Create a document using the internal representation
    expected by the RAG pipeline.
    """

    return {
        "document_id": document_id,
        "version": version,
        "title": title,
        "source": source,
        "source_type": source_type,
        "text": text,
        "metadata": metadata or {},
    }