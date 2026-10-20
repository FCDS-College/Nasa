import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List
from tests.eval.mock_rag import MockRAGSystem

class RAGConnector:
    """
    موصل موحد لنظام الـ RAG (Unified RAG Connector):
    يدعم العمل إما بنظام المحاكاة المحلي (mock mode) أو الاتصال المباشر بـ REST API
    الخاص بالفريق (apps/api) عند تشغيله.
    """
    def __init__(self, mode: str = "mock", api_base_url: str = "http://localhost:8000"):
        self.mode = mode.lower()
        self.api_base_url = api_base_url.rstrip("/")
        self.mock_rag = MockRAGSystem()

    def query(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        if self.mode == "mock":
            return self.mock_rag.query(user_query, top_k=top_k)

        elif self.mode == "api":
            url = f"{self.api_base_url}/api/search"
            payload = json.dumps({"query": user_query, "top_k": top_k}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    results = data.get("results", [])
                    return {
                        "query": user_query,
                        "answer": data.get("answer", "لا توجد إجابة مسترجعة."),
                        "retrieved_context": [r.get("text", "") for r in results],
                        "retrieved_doc_ids": [r.get("doc_id", "") for r in results],
                        "citations": data.get("citations", [])
                    }
            except Exception as e:
                # عند تعذر الاتصال بالـ API الحقيقي، نسجل الخطأ ونوفر رد طوارئ
                return {
                    "query": user_query,
                    "answer": f"API Connection Error: {str(e)}",
                    "retrieved_context": [],
                    "retrieved_doc_ids": [],
                    "citations": []
                }
        else:
            raise ValueError(f"Unknown RAG connector mode: {self.mode}. Choose 'mock' or 'api'.")
