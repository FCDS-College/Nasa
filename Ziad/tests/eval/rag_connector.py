import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List
from tests.eval.mock_rag import MockRAGSystem

class RAGConnector:
    """
    موصل موحد لنظام الـ RAG (Unified RAG Connector - B4 Compliant):
    - وضع المحاكاة (mock mode): للاختبارات السريعة والعزل.
    - وضع الـ API الحقيقي:
        * يستخدم GET /api/search?q=...&page_size=... للاسترجاع وتعيين result_id/evidence_id.
        * يستخدم POST /api/chat للإجابة وتوليد الاستشهادات.
        * عند حدوث أي خطأ شبكي أو خطأ HTTP، يطلق Exception فوراً ليفشل الـ Run ولا يبتلع الخطأ.
    """
    def __init__(self, mode: str = "mock", api_base_url: str = "http://localhost:8000"):
        self.mode = mode.lower()
        self.api_base_url = api_base_url.rstrip("/")
        self.mock_rag = MockRAGSystem()

    def query(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        if self.mode == "mock":
            return self.mock_rag.query(user_query, top_k=top_k)

        elif self.mode == "api":
            # 1. استدعاء GET /api/search لجمع وثائق الاسترجاع
            params = urllib.parse.urlencode({"q": user_query, "page_size": top_k})
            search_url = f"{self.api_base_url}/api/search?{params}"
            search_req = urllib.request.Request(search_url, headers={"Accept": "application/json"})

            try:
                with urllib.request.urlopen(search_req, timeout=10) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP Error {resp.status} on GET /api/search")
                    search_data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                # B4: لا نبتلع الخطأ أبداً بل نرمي Exception صريح
                raise RuntimeError(f"❌ فشل استدعاء GET /api/search: {str(e)}") from e

            # مطابقة الحقول المعيارية للـ API: result_id, evidence_id, document_id, locator
            raw_results = search_data.get("results", [])
            retrieved_context = []
            retrieved_doc_ids = []

            for r in raw_results:
                # تفضيل evidence_id ثم result_id ثم document_id
                doc_id = r.get("evidence_id") or r.get("result_id") or r.get("document_id") or ""
                if doc_id:
                    retrieved_doc_ids.append(str(doc_id))
                text_snippet = r.get("text") or r.get("content") or r.get("snippet") or ""
                retrieved_context.append(text_snippet)

            # 2. استدعاء POST /api/chat للحصول على الإجابة والاستشهادات
            chat_url = f"{self.api_base_url}/api/chat"
            chat_payload = json.dumps({"message": user_query, "stream": False}).encode("utf-8")
            chat_req = urllib.request.Request(
                chat_url,
                data=chat_payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST"
            )

            try:
                with urllib.request.urlopen(chat_req, timeout=15) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP Error {resp.status} on POST /api/chat")
                    chat_data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                # B4: إثارة استثناء وفشل التشغيل فوراً
                raise RuntimeError(f"❌ فشل استدعاء POST /api/chat: {str(e)}") from e

            answer = chat_data.get("answer") or chat_data.get("response") or chat_data.get("message") or ""
            citations = chat_data.get("citations") or chat_data.get("sources") or []

            return {
                "query": user_query,
                "answer": answer,
                "retrieved_context": retrieved_context,
                "retrieved_doc_ids": retrieved_doc_ids,
                "citations": citations
            }
        else:
            raise ValueError(f"Unknown RAG connector mode: {self.mode}. Choose 'mock' or 'api'.")
