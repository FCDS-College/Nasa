class CitationManager:

    """Builds citation records from context sources.

    The citation id equals the chunk id. Document version and locator are preserved so a citation can be traced back to its source (see docs/ai/citation-provenance.md)."""

    def create_citations(self, sources):
        """Create one citation dict per source.

        Args:
            sources: list of dicts with chunk_id, document_id, document_version and optionally metadata and locator.

        Returns:
            List of citations with citation_id, chunk_id, document_id, document_version, metadata and (when present) locator.

        Raises:
            KeyError: if a source lacks chunk_id, document_id or document_version."""

        citations = []

        for source in sources:

            citation = {
                "citation_id": source["chunk_id"],
                "chunk_id": source["chunk_id"],
                "document_id": source["document_id"],
                "document_version": source["document_version"],
                "metadata": source.get(
                    "metadata",
                    {}
                )
            }

            # Preserve the shared locator used by
            # the retrieval DTO and provenance chain.
            locator = source.get("locator")

            if locator is not None:

                if hasattr(locator, "model_dump"):
                    locator = locator.model_dump()

                citation["locator"] = locator

            citations.append(citation)

        return citations

    def attach_citations(self, context_result):
        """Add citations to a context result.

        Args:
            context_result: dict with `context` and `sources` (output of ContextBuilder.build).

        Returns:
            Dict with `context`, `sources` and `citations`."""

        sources = context_result.get(
            "sources",
            []
        )

        citations = self.create_citations(
            sources
        )

        return {
            "context": context_result.get(
                "context",
                ""
            ),
            "sources": sources,
            "citations": citations
        }

