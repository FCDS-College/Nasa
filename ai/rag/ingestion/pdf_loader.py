from pathlib import Path

from pypdf import PdfReader

from ai.rag.ingestion.document import create_document


class PDFDocumentLoader:

    """Loads a PDF as one document per page.

    Each document has id "<stem>_page_<n>", version "1", metadata domain="combustion" (hard-coded) and locator {"page": n}."""

    def load(self, source):
        """
        Load a PDF as page-level documents.

        Each PDF page becomes a separate document so that
        page numbers can be preserved as retrieval locators.

        Parameters
        ----------
        source:
            Path to a PDF file.

        Returns
        -------
        list[dict]
            One document per PDF page.
        """

        pdf_path = Path(source)

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"PDF file not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                "source must be a PDF file."
            )

        reader = PdfReader(str(pdf_path))

        documents = []

        document_id = pdf_path.stem

        for page_index, page in enumerate(reader.pages):

            text = page.extract_text() or ""

            page_number = page_index + 1

            documents.append(
                create_document(
                    document_id=(
                        f"{document_id}_page_{page_number}"
                    ),
                    title=pdf_path.stem,
                    source=str(pdf_path),
                    source_type="pdf",
                    text=text,
                    version="1",
                    metadata={
                        "domain": "combustion",
                        "page": page_number,
                        "locator": {
                            "page": page_number
                        }
                    }
                )
            )

        return documents
