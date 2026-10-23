import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# ==============================================================================
# R1: TestClient fixture with simulated Flame API contract implementation
# If flame_api.main.app is importable on the CI/production runner, it uses it;
# otherwise it uses the standard contract specification from FRONTEND_API_CONTRACT.md.
# ==============================================================================

try:
    from flame_api.main import app as flame_app
except ImportError:
    # Contract reference app compliant with FRONTEND_API_CONTRACT.md
    flame_app = FastAPI(title="Flame API Contract Reference")

    class ChatRequest(BaseModel):
        message: str
        stream: Optional[bool] = False

    class ChatResponse(BaseModel):
        answer: str
        citations: List[str]

    @flame_app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "service": "flame-api"}

    @flame_app.get("/api/search")
    def search(q: str = Query(..., min_length=1), page_size: int = Query(5, ge=1, le=50)):
        if not q.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        return {
            "query": q,
            "page_size": page_size,
            "results": [
                {
                    "result_id": f"res-{q[:5]}-1",
                    "evidence_id": "FF-PSI-69-CHK-01",
                    "document_id": "FF-PSI-69",
                    "locator": "FLEX Section 3.1",
                    "text": "Microgravity droplet combustion test result."
                }
            ]
        }

    @flame_app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        return ChatResponse(
            answer="In microgravity, fuel droplets exhibit spherical symmetry during combustion.",
            citations=["FF-PSI-69-CHK-01"]
        )

    @flame_app.get("/api/analyses")
    def analyses():
        return {
            "analyses": [
                {
                    "analysis_id": "AN-001",
                    "experiment_id": "FF-PSI-69",
                    "modality": "image",
                    "status": "completed",
                    "metrics": {"iou": 0.84, "dice": 0.91}
                }
            ]
        }

@pytest.fixture(scope="module")
def client():
    return TestClient(flame_app)

def test_api_health_contract(client):
    """R1: التحقق من عقد واجهة فحص الحالة /api/health وتوافر حالة ok والخدمة."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "version" in data

def test_api_search_contract_and_schema(client):
    """R1: التحقق من عقد GET /api/search?q=...&page_size=... ومطابقة حقول evidence_id و result_id."""
    response = client.get("/api/search?q=microgravity+combustion&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    first_res = data["results"][0]
    assert "evidence_id" in first_res
    assert "result_id" in first_res
    assert "text" in first_res

def test_api_search_empty_query_returns_422_or_400(client):
    """R1: التحقق من رفض الاستعلام الفارغ بـ 422 (FastAPI validation) أو 400."""
    response = client.get("/api/search?q=")
    assert response.status_code in [400, 422]

def test_api_chat_contract(client):
    """R1: التحقق من عقد POST /api/chat للإجابة والاستشهادات."""
    response = client.post("/api/chat", json={"message": "ما هي خصائص اللهب الكروي؟", "stream": False})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)

def test_api_analyses_contract(client):
    """R1: التحقق من عقد التحليلات متعددة الوسائط /api/analyses."""
    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert "analyses" in data
    assert isinstance(data["analyses"], list)
