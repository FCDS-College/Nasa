from abc import ABC, abstractmethod


class Chunker(ABC):

    @abstractmethod
    def chunk(self, document):
        """
        Split a document into smaller retrievable chunks.
        """
        pass


class SimpleChunker(Chunker):

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

            start = next_start

        return chunks
