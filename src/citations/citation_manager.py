class CitationManager:

    def create_citations(self, sources):
        """
        Create citations from retrieved sources.

        Parameters
        ----------
        sources : list[dict]
            Sources selected by the Context Builder.

        Returns
        -------
        list[dict]
            Citation information for each source.
        """

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

            citations.append(citation)

        return citations

    def attach_citations(self, context_result):
        """
        Attach citations to a context-building result.
        """

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
    