from typing import Dict, Any
from tests.eval.mock_rag import MockRAGSystem

class RAGConnector:
    """
    موصل موحد لنظام الـ RAG (Unified RAG Connector):
    يدعم نظام المحاكاة المحلي (mock mode) فقط. نمط api غير مدعوم حالياً (انظر NotImplementedError).
    """
    def __init__(self, mode: str = "mock", api_base_url: str = "http://localhost:8000"):
        self.mode = mode.lower()
        self.api_base_url = api_base_url.rstrip("/")
        self.mock_rag = MockRAGSystem()

    def query(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        if self.mode == "mock":
            return self.mock_rag.query(user_query, top_k=top_k)

        elif self.mode == "api":
            # This mode POSTed JSON to /api/search, which is `GET /api/search?q=...` with a different result shape,
            # swallowed the failure and returned the error text as the system's "answer" (scored as a system failure).
            raise NotImplementedError(
                "RAGConnector api mode does not match /api/search (GET ?q=, different result shape). "
                "Use ai/rag/evaluation/flame_retrieval_benchmark.py to evaluate the live API."
            )
        else:
            raise ValueError(f"Unknown RAG connector mode: {self.mode}. Choose 'mock' or 'api'.")
