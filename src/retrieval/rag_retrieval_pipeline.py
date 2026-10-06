from src.retrieval.metadata_filter import MetadataFilter
from src.retrieval.hybrid_search import HybridSearchService
from src.reranking.reranker import Reranker
from src.context.context_builder import ContextBuilder
from src.citations.citation_manager import CitationManager


class RAGRetrievalPipeline:

    def __init__(
        self,
        vector_search,
        keyword_search,
        embedding_service
    ):
        self.embedding_service = embedding_service

        self.metadata_filter = MetadataFilter()

        self.hybrid_search = HybridSearchService(
            vector_search=vector_search,
            keyword_search=keyword_search
        )

        self.reranker = Reranker()

        self.context_builder = ContextBuilder()

        self.citation_manager = CitationManager()

    def retrieve(
        self,
        query,
        chunks,
        metadata_filters=None,
        top_k=5
    ):
        """
        End-to-end retrieval pipeline.

        Flow:
        Metadata Filtering
        → Hybrid Search
        → Reranking
        → Context Building
        → Citation Generation
        """

        # Step 1: Metadata filtering
        filtered_chunks = self.metadata_filter.filter(
            chunks,
            metadata_filters or {}
        )

        if not filtered_chunks:
            return {
                "query": query,
                "context": "",
                "sources": [],
                "citations": [],
                "results": []
            }

        # Step 2: Create query embedding
        query_embedding = self.embedding_service.embed_text(
            query
        )

        # Step 3: Hybrid retrieval
        retrieval_results = self.hybrid_search.search(
            chunks=filtered_chunks,
            query=query,
            query_embedding=query_embedding,
            top_k=top_k
        )

        # Step 4: Reranking
        reranked_results = self.reranker.rerank(
            query=query,
            results=retrieval_results,
            top_k=top_k
        )

        # Step 5: Build context
        context_result = self.context_builder.build(
            reranked_results
        )

        # Step 6: Generate citations
        cited_result = self.citation_manager.attach_citations(
            context_result
        )

        return {
            "query": query,
            "context": cited_result["context"],
            "sources": cited_result["sources"],
            "citations": cited_result["citations"],
            "results": reranked_results
        }