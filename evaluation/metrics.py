def recall_at_k(retrieved_chunks, relevant_chunks, k):
    """
    Calculate Recall@K.

    Recall@K =
    relevant retrieved chunks within top K
    ------------------------------------------------
    total relevant chunks
    """

    retrieved_top_k = retrieved_chunks[:k]

    retrieved_ids = {
        result["chunk"]["chunk_id"]
        for result in retrieved_top_k
    }

    relevant_ids = set(relevant_chunks)

    if not relevant_ids:
        return 0.0

    retrieved_relevant = (
        retrieved_ids & relevant_ids
    )

    return len(retrieved_relevant) / len(relevant_ids)


def reciprocal_rank(retrieved_chunks, relevant_chunks):
    """
    Calculate Reciprocal Rank.

    Returns:
        1 / rank of first relevant result
    """

    relevant_ids = set(relevant_chunks)

    for rank, result in enumerate(
        retrieved_chunks,
        start=1
    ):

        chunk_id = result["chunk"]["chunk_id"]

        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def citation_coverage(citations, relevant_chunks):
    """
    Calculate citation/source coverage.

    Measures how many expected relevant chunks
    are represented in the generated citations.
    """

    cited_ids = {
        citation["chunk_id"]
        for citation in citations
    }

    relevant_ids = set(relevant_chunks)

    if not relevant_ids:
        return 0.0

    covered = cited_ids & relevant_ids

    return len(covered) / len(relevant_ids)