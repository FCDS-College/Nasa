from typing import Dict, Any
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

class MockRAGSystem:
    """
    محاكي لنظام الـ RAG المتوقع من الفريق (Engineer 1).
    يحاكي سلوك استرجاع الوثائق وتوليد الإجابات للاستخدام في تطوير وتشغيل واجهات التقييم.
    """
    def __init__(self, simulation_mode: str = "perfect"):
        self.simulation_mode = simulation_mode

    def query(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        استقبال الاستعلام وتوليد إجابة افتراضية مع الوثائق المسترجعة والاقتباسات.
        """
        # محاكاة إجابة مستندة لوثائق ناسا
        if "لهب" in user_query or "combustion" in user_query.lower() or "فلورسنت" in user_query:
            retrieved_docs = [
                {"doc_id": "DOC-001-P15", "score": 0.94, "text": "في غياب الجاذبية، يتشكل اللهب بصورة كروية متماثلة."},
                {"doc_id": "DOC-001-P18", "score": 0.88, "text": "صورة اللهب الكروي الأزرق حول قطرة هيبتان."},
                {"doc_id": "DOC-002-P34", "score": 0.81, "text": "رصد استمرار الاحتراق البارد."}
            ]
            answer = "يتشكل اللهب في بيئة الجاذبية الصغرى بصورة كروية متماثلة طبقاً لـ NASA-TM-2024-0012."
            citations = ["DOC-001-P15"]
        else:
            retrieved_docs = [
                {"doc_id": "DOC-GEN-001", "score": 0.65, "text": "معلومات عامة حول أبحاث الفضاء والفيزياء."}
            ]
            answer = "المعلومات المطلوبة غير كافية لتأكيد الإجابة من المصادر الفضائية المعتمدة."
            citations = []

        return {
            "query": user_query,
            "answer": answer,
            "retrieved_context": [d["text"] for d in retrieved_docs[:top_k]],
            "retrieved_doc_ids": [d["doc_id"] for d in retrieved_docs[:top_k]],
            "citations": citations
        }
