from ai.rag.dto import (
    EvidenceBundle,
    RetrievalRequest,
    RetrievedChunk,
    Locator
)

from ai.rag.retrieval.metadata_filter import MetadataFilter
from ai.rag.retrieval.hybrid_search import HybridSearchService
from ai.rag.reranking.reranker import Reranker
from ai.rag.context.context_builder import ContextBuilder
from ai.rag.citations.citation_manager import CitationManager


class RAGRetrievalPipeline:

    """End-to-end retrieval: default domain filter, metadata filter, hybrid search, evidence check, rerank, context building and citations.

    Returns an EvidenceBundle with status "insufficient_evidence" when the filters leave no chunks or no chunk passes the vector minimum score."""

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

    def _apply_default_domain_filter(
        self,
        query,
        metadata_filters
    ):
        """
        Apply a default domain filter for
        combustion-related queries.

        Combustion queries must only retrieve
        chunks from the combustion domain.

        Explicit metadata filters are preserved.
        """

        filters = dict(metadata_filters or {})

        query_lower = query.lower()

        if "combustion" in query_lower:
            filters.setdefault(
                "domain",
                "combustion"
            )

        return filters

    def _build_evidence_bundle(
        self,
        query,
        reranked_results,
        context_result,
        cited_result
    ):
        """
        Convert retrieval results into the
        EvidenceBundle DTO.
        """

        evidence = []

        for result in reranked_results:

            chunk = result["chunk"]

            metadata = chunk.get(
                "metadata",
                {}
            )

            locator_data = metadata.get(
                "locator"
            )

            locator = None

            if locator_data:
                locator = Locator(
                    **locator_data
                )

            evidence.append(
                RetrievedChunk(
                    chunk_id=chunk["chunk_id"],
                    document_id=chunk["document_id"],
                    document_version=(
                        chunk["document_version"]
                    ),
                    text=chunk["text"],
                    score=float(
                        result.get(
                            "rerank_score",
                            result.get(
                                "hybrid_score",
                                0.0
                            )
                        )
                    ),
                    locator=locator,
                    metadata=metadata
                )
            )

        return EvidenceBundle(
           query=query,
           evidence=evidence,
           context=cited_result["context"],
           citations=cited_result["citations"],
           results=reranked_results,
           status="ok"
        )

    def retrieve(
        self,
        query=None,
        chunks=None,
        metadata_filters=None,
        top_k=5,
        request=None
    ):
        """
        End-to-end retrieval pipeline.

        Supports either:

        1. The existing parameter-based API.

        2. A RetrievalRequest DTO through
           the request parameter.

        Flow:

        Retrieval Request
        → Default Domain Filtering
        → Metadata Filtering
        → Hybrid Search
        → Evidence Check
        → Reranking
        → Context Building
        → Citation Generation
        → EvidenceBundle
        """

        if request is not None:

            if not isinstance(
                request,
                RetrievalRequest
            ):
                raise TypeError(
                    "request must be a RetrievalRequest."
                )

            query = request.query
            top_k = request.top_k
            metadata_filters = request.filters

        if query is None:
            raise ValueError(
                "query is required."
            )

        if chunks is None:
            raise ValueError(
                "chunks are required."
            )

        effective_filters = (
            self._apply_default_domain_filter(
                query,
                metadata_filters
            )
        )

        filtered_chunks = self.metadata_filter.filter(
            chunks,
            effective_filters
        )

        if not filtered_chunks:
            return EvidenceBundle(
                query=query,
                status="insufficient_evidence"
            )

        query_embedding = (
            self.embedding_service.embed_text(
                query
            )
        )

        retrieval_results = (
            self.hybrid_search.search(
                chunks=filtered_chunks,
                query=query,
                query_embedding=query_embedding,
                top_k=top_k
            )
        )

        # Check whether any semantic evidence
        # passes the vector-search minimum score.
        semantic_results = (
            self.hybrid_search.vector_search.search(
                query_embedding,
                top_k=top_k,
                chunks=filtered_chunks
            )
        )

        if not semantic_results:
            return EvidenceBundle(
                query=query,
                status="insufficient_evidence"
            )

        reranked_results = (
            self.reranker.rerank(
                query=query,
                results=retrieval_results,
                top_k=top_k
            )
        )

        context_result = (
            self.context_builder.build(
                reranked_results
            )
        )

        cited_result = (
            self.citation_manager.attach_citations(
                context_result
            )
        )

        return self._build_evidence_bundle(
            query=query,
            reranked_results=reranked_results,
            context_result=context_result,
            cited_result=cited_result
        )
