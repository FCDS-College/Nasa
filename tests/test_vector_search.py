from src.ingestion.chunker import SimpleChunker

from src.retrieval.vector_search import VectorSearchService


def test_vector_search(fake_embedding_service):

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
        ) * 20,
        "metadata": {}
    }

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    chunks = chunker.chunk(document)

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = fake_embedding_service.embed_batch(
        texts
    )

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    query = "How does microgravity affect flames?"

    query_embedding = fake_embedding_service.embed_text(
        query
    )

    results = vector_search.search(
        query_embedding,
        top_k=3
    )

    assert len(results) == 3

    for result in results:

        assert "chunk" in result
        assert "score" in result

        print("\nScore:", result["score"])
        print(
            "Chunk:",
            result["chunk"]["chunk_id"]
        )
        print(
            "Text:",
            result["chunk"]["text"][:100]
        )


def test_vector_search_respects_filtered_chunks(
    fake_embedding_service
):

    chunks = [
        {
            "chunk_id": "combustion_chunk",
            "document_id": "doc_1",
            "document_version": "1",
            "text": (
                "Microgravity affects flame behavior."
            ),
            "metadata": {
                "domain": "combustion"
            }
        },
        {
            "chunk_id": "dsi_chunk",
            "document_id": "doc_2",
            "document_version": "1",
            "text": (
                "DSI information unrelated "
                "to combustion."
            ),
            "metadata": {
                "domain": "DSI"
            }
        }
    ]

    embeddings = fake_embedding_service.embed_batch(
        [
            chunk["text"]
            for chunk in chunks
        ]
    )

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    query = "How does microgravity affect flames?"

    query_embedding = fake_embedding_service.embed_text(
        query
    )

    # Only the combustion chunk is allowed
    # to be searched.
    filtered_chunks = [
        chunks[0]
    ]

    results = vector_search.search(
        query_embedding,
        top_k=5,
        chunks=filtered_chunks
    )

    assert len(results) == 1

    assert (
        results[0]["chunk"]["chunk_id"]
        == "combustion_chunk"
    )


def test_vector_search_returns_empty_for_low_scores(
    fake_embedding_service
):

    chunks = [
        {
            "chunk_id": "chunk_1",
            "document_id": "doc_1",
            "document_version": "1",
            "text": (
                "Microgravity affects flame behavior."
            ),
            "metadata": {}
        },
        {
            "chunk_id": "chunk_2",
            "document_id": "doc_2",
            "document_version": "1",
            "text": (
                "Earth gravity produces stronger "
                "buoyancy."
            ),
            "metadata": {}
        }
    ]

    embeddings = fake_embedding_service.embed_batch(
        [
            chunk["text"]
            for chunk in chunks
        ]
    )

    vector_search = VectorSearchService(
        min_score=0.99
    )

    vector_search.add_documents(
        chunks,
        embeddings
    )

    query = (
        "What is the chemical composition "
        "of Saturn?"
    )

    query_embedding = fake_embedding_service.embed_text(
        query
    )

    results = vector_search.search(
        query_embedding,
        top_k=5
    )

    assert results == []
