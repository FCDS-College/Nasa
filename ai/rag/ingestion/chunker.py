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
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document):

        text = document["text"]

        chunks = []

        start = 0
        chunk_index = 0

        while start < len(text):

            end = start + self.chunk_size

            chunk_text = text[start:end]

            chunks.append({
                "chunk_id": f'{document["document_id"]}_chunk_{chunk_index}',
                "document_id": document["document_id"],
                "document_version": document["version"],
                "text": chunk_text,
                "chunk_index": chunk_index,
                "metadata": document["metadata"],
            })

            chunk_index += 1

            if end >= len(text):
                break

            start = end - self.overlap

        return chunks 