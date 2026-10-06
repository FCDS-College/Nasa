from src.ingestion.chunker import SimpleChunker


def test_chunker():

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": "A" * 1200,
        "metadata": {}
    }

    chunker = SimpleChunker(
        chunk_size=500,
        overlap=50
    )

    chunks = chunker.chunk(document)

    assert len(chunks) > 1

    assert chunks[0]["document_id"] == "test_001"

    assert chunks[0]["document_version"] == "1"

    assert chunks[0]["chunk_id"] == "test_001_chunk_0"

def test_chunker_rejects_invalid_overlap():

    try:
        SimpleChunker(
            chunk_size=100,
            overlap=100
        )
    except ValueError:
        return

    assert False, "Chunker should reject overlap >= chunk_size"


def test_chunker_preserves_word_boundaries():

    document = {
        "document_id": "test_002",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior "
            "and changes the flow around flames."
        ),
        "metadata": {}
    }

    chunker = SimpleChunker(
        chunk_size=30,
        overlap=5
    )

    chunks = chunker.chunk(document)

    original_words = set(
        document["text"].split()
    )

    for chunk in chunks:

        chunk_text = chunk["text"].strip()

        # Every chunk should start and end with a complete word.
        first_word = chunk_text.split()[0]
        last_word = chunk_text.split()[-1]

        assert first_word in original_words
        assert last_word in original_words
