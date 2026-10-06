class CitationManager:

    def create_citations(self, sources):
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

