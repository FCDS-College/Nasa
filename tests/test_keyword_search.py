from src.retrieval.keyword_search import KeywordSearchService


def test_keyword_search():

    chunks = [
        {
            "chunk_id": "chunk_1",
            "text": (
                "Microgravity affects flame behavior "
                "and changes the flow around flames."
            ),
            "metadata": {}
        },
        {
            "chunk_id": "chunk_2",
            "text": (
                "Earth gravity causes stronger buoyancy "
                "driven flow."
            ),
            "metadata": {}
        },
        {
            "chunk_id": "chunk_3",
            "text": (
                "Microgravity experiments study combustion "
                "and flame behavior."
            ),
            "metadata": {}
        }
    ]

    keyword_search = KeywordSearchService()

    results = keyword_search.search(
        chunks,
        "microgravity flame",
        top_k=2
    )

    assert len(results) == 2

    assert results[0]["chunk"]["chunk_id"] == "chunk_1"

    assert results[0]["score"] > 0

    assert "chunk" in results[0]
    assert "score" in results[0]

def test_keyword_search_does_not_use_substring_matching():
    from src.retrieval.keyword_search import KeywordSearchService

    chunks = [
        {
            "chunk_id": "chunk_1",
            "text": "The plasma properties were measured.",
            "metadata": {}
        },
        {
            "chunk_id": "chunk_2",
            "text": "The flame temperature was measured.",
            "metadata": {}
        }
    ]

    service = KeywordSearchService()

    results = service.search(
        chunks=chunks,
        query="is a",
        top_k=5
    )

    assert results == []
