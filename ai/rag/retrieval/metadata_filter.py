class MetadataFilter:

    """Exact-match metadata filter: a chunk is kept only if every filter key equals its metadata value. Empty filters keep all chunks."""
    def filter(self, chunks, filters):
        """
        Filter chunks based on metadata values.

        Parameters
        ----------
        chunks : list[dict]
            Chunks to filter.

        filters : dict
            Metadata conditions, for example:
            {"environment": "microgravity"}

        Returns
        -------
        list[dict]
            Chunks matching all filters.
        """

        if not filters:
            return chunks

        filtered_chunks = []

        for chunk in chunks:

            metadata = chunk.get("metadata", {})

            matches = True

            for key, expected_value in filters.items():

                if metadata.get(key) != expected_value:
                    matches = False
                    break

            if matches:
                filtered_chunks.append(chunk)

        return filtered_chunks