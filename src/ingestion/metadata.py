def merge_metadata(document_metadata, extra_metadata=None):
    """
    Merge document metadata with additional metadata.
    """

    metadata = dict(document_metadata or {})

    if extra_metadata:
        metadata.update(extra_metadata)

    return metadata