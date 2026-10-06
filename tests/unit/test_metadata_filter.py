from ai.rag.retrieval.metadata_filter import MetadataFilter


def test_metadata_filter():

    chunks = [
        {
            "chunk_id": "chunk_1",
            "metadata": {
                "environment": "microgravity",
                "source_type": "NASA"
            }
        },
        {
            "chunk_id": "chunk_2",
            "metadata": {
                "environment": "earth",
                "source_type": "NASA"
            }
        },
        {
            "chunk_id": "chunk_3",
            "metadata": {
                "environment": "microgravity",
                "source_type": "paper"
            }
        }
    ]

    metadata_filter = MetadataFilter()

    results = metadata_filter.filter(
        chunks,
        {
            "environment": "microgravity"
        }
    )

    assert len(results) == 2

    assert results[0]["chunk_id"] == "chunk_1"
    assert results[1]["chunk_id"] == "chunk_3"
    