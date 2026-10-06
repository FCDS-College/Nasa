class ContextBuilder:

    def __init__(
        self,
        max_chunks=5,
        max_characters=4000
    ):
        self.max_chunks = max_chunks
        self.max_characters = max_characters

    def build(self, results):
        selected_chunks = []
        seen_chunk_ids = set()
        total_characters = 0

        for result in results:

            chunk = result["chunk"]
            chunk_id = chunk["chunk_id"]

            if chunk_id in seen_chunk_ids:
                continue

            chunk_text = chunk["text"]

            if (
                total_characters + len(chunk_text)
                > self.max_characters
            ):
                break

            selected_chunk = {
                "chunk_id": chunk_id,
                "document_id": chunk["document_id"],
                "document_version": chunk["document_version"],
                "text": chunk_text,
                "metadata": chunk.get(
                    "metadata",
                    {}
                )
            }

            # Preserve the shared locator so it can
            # flow through context and citation generation.
            locator = chunk.get("locator")

            if locator is None:
                locator = chunk.get(
                    "metadata",
                    {}
                ).get("locator")

            if locator is not None:
                selected_chunk["locator"] = locator

            selected_chunks.append(
                selected_chunk
            )

            seen_chunk_ids.add(chunk_id)
            total_characters += len(chunk_text)

            if len(selected_chunks) >= self.max_chunks:
                break

        context_parts = []

        for chunk in selected_chunks:
            context_parts.append(
                f"[{chunk['chunk_id']}]\n"
                f"{chunk['text']}"
            )

        context = "\n\n".join(context_parts)

        return {
            "context": context,
            "sources": selected_chunks
        }
