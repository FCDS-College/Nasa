from ai.rag.ingestion.chunker import SimpleChunker

from ai.rag.embeddings.embedding_service import (
    SentenceTransformerEmbeddingService
)

from ai.rag.retrieval.vector_search import VectorSearchService
from ai.rag.retrieval.keyword_search import KeywordSearchService
from ai.rag.retrieval.rag_retrieval_pipeline import (
    RAGRetrievalPipeline
)

from ai.rag.evaluation.evaluation_dataset import (
    EVALUATION_DATASET
)

from ai.rag.evaluation.metrics import (
    recall_at_k,
    reciprocal_rank,
    citation_coverage
)


def build_test_chunks():

    document = {
        "document_id": "test_001",
        "version": "1",
        "text": (
            "Microgravity affects flame behavior. "
            "Buoyancy is reduced in microgravity. "
            "This changes the flow around flames. "
            "Combustion experiments study flame behavior. "
            "Earth gravity produces stronger buoyancy driven flow. "
        ) * 10,

        "metadata": {
            "environment": "microgravity",
            "source_type": "test"
        }
    }

    chunker = SimpleChunker(
        chunk_size=200,
        overlap=30
    )

    return chunker.chunk(document)


def main():

    print("\n==============================")
    print("BUILDING TEST CORPUS")
    print("==============================")

    chunks = build_test_chunks()

    embedding_service = SentenceTransformerEmbeddingService()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_service.embed_batch(
        texts
    )

    vector_search = VectorSearchService()

    vector_search.add_documents(
        chunks,
        embeddings
    )

    keyword_search = KeywordSearchService()

    pipeline = RAGRetrievalPipeline(
        vector_search=vector_search,
        keyword_search=keyword_search,
        embedding_service=embedding_service
    )

    print("Number of chunks:", len(chunks))

    # -------------------------
    # Evaluation
    # -------------------------

    recall_scores = []
    reciprocal_rank_scores = []
    citation_scores = []

    for item in EVALUATION_DATASET:

        question = item["question"]
        relevant_chunks = item["relevant_chunks"]

        result = pipeline.retrieve(
            query=question,
            chunks=chunks,
            metadata_filters={
                "environment": "microgravity"
            },
            top_k=5
        )

        retrieval_results = result["results"]

        recall = recall_at_k(
            retrieval_results,
            relevant_chunks,
            k=5
        )

        rr = reciprocal_rank(
            retrieval_results,
            relevant_chunks
        )

        citation = citation_coverage(
            result["citations"],
            relevant_chunks
        )

        recall_scores.append(recall)
        reciprocal_rank_scores.append(rr)
        citation_scores.append(citation)

        print("\n------------------------------")
        print("Question:")
        print(question)

        print("Recall@5:", round(recall, 3))
        print("Reciprocal Rank:", round(rr, 3))
        print(
            "Citation Coverage:",
            round(citation, 3)
        )

    # -------------------------
    # Average metrics
    # -------------------------

    mean_recall = (
        sum(recall_scores)
        / len(recall_scores)
    )

    mean_rr = (
        sum(reciprocal_rank_scores)
        / len(reciprocal_rank_scores)
    )

    mean_citation = (
        sum(citation_scores)
        / len(citation_scores)
    )

    print("\n==============================")
    print("BASELINE EVALUATION RESULTS")
    print("==============================")

    print(
        "Mean Recall@5:",
        round(mean_recall, 3)
    )

    print(
        "Mean Reciprocal Rank:",
        round(mean_rr, 3)
    )

    print(
        "Mean Citation Coverage:",
        round(mean_citation, 3)
    )


if __name__ == "__main__":
    main()