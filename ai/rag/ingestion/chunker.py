from abc import ABC, abstractmethod


class Chunker(ABC):

    """Abstract interface that splits a document into retrievable chunks."""
    @abstractmethod
    def chunk(self, document):
        """
        Split a document into smaller retrievable chunks.
        """
        pass


class SimpleChunker(Chunker):

    """Fixed-size character chunker with overlap that breaks on word boundaries.

    Raises:
        ValueError: if chunk_size <= 0, overlap < 0 or overlap >= chunk_size."""

    def __init__(self, chunk_size=500, overlap=50):

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than 0."
            )

        if overlap < 0:
            raise ValueError(
                "overlap must be greater than or equal to 0."
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document):

        """Split a document into chunks.

        Args:
            document: dict with document_id, version, text and metadata.

        Returns:
            List of chunk dicts: chunk_id ("<document_id>_chunk_<n>"), document_id, document_version, text, chunk_index, metadata. The metadata dict is shared by reference with the document.

        Raises:
            KeyError: if document lacks a required key."""

        text = document["text"]

        chunks = []

        start = 0
        chunk_index = 0

        while start < len(text):

            end = min(
                start + self.chunk_size,
                len(text)
            )

            # Move the end backward until we reach
            # a word boundary.
            if end < len(text):

                while end > start and not text[end].isspace():
                    end -= 1

            # Safety fallback for a single word longer
            # than the chunk size.
            if end == start:
                end = min(
                    start + self.chunk_size,
                    len(text)
                )

            chunk_text = text[start:end].strip()

            if chunk_text:

                chunks.append({
                    "chunk_id": (
                        f'{document["document_id"]}'
                        f'_chunk_{chunk_index}'
                    ),
                    "document_id": document["document_id"],
                    "document_version": document["version"],
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "metadata": document["metadata"],
                })

                chunk_index += 1

            if end >= len(text):
                break

            # Start the next chunk with overlap.
            next_start = end - self.overlap

            # Move the new start to a word boundary.
            while (
                next_start < end
                and next_start > 0
                and not text[next_start - 1].isspace()
            ):
                next_start += 1

            # The overlap can reach back past this chunk's own start (a short word followed by a long
            # unbroken token), which made `start` negative and the loop endless. Never move backwards:
            # without room for an overlap, the next chunk begins where this one ended.
            if next_start <= start:
                next_start = end

            if next_start <= start:
                raise RuntimeError("chunker made no progress")

            start = next_start

        return chunks
