import json
import pytest
import http.server
import threading
from tests.eval.rag_connector import RAGConnector

class MockAPIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/search"):
            body = json.dumps({
                "results": [
                    {"evidence_id": "FF-PSI-69-CHK-01", "text": "FLEX droplet burning test evidence.", "result_id": "res-1"},
                    {"evidence_id": "FF-PSI-98-CHK-02", "text": "SAFFIRE flame spread evidence.", "result_id": "res-2"}
                ]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 0:
            _ = self.rfile.read(content_len)

        if self.path == "/api/chat":
            body = json.dumps({
                "answer": "يتشكل اللهب كروياً طبقاً لبيانات تجربة FLEX (FF-PSI-69).",
                "citations": ["FF-PSI-69-CHK-01"]
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # منع طباعة سجلات السيرفر في الكونسول

@pytest.fixture(scope="module")
def mock_api_server():
    server = http.server.HTTPServer(("127.0.0.1", 8999), MockAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:8999"
    server.shutdown()

def test_rag_connector_api_mode_success(mock_api_server):
    """التحقق من أن RAGConnector يستدعي GET /api/search و POST /api/chat بنجاح ويستخلص الحقول المطلوبة."""
    connector = RAGConnector(mode="api", api_base_url=mock_api_server)
    res = connector.query("ما هي آلية احتراق القطرات؟", top_k=2)

    assert "FF-PSI-69-CHK-01" in res["retrieved_doc_ids"]
    assert len(res["retrieved_context"]) == 2
    assert "FLEX" in res["answer"]
    assert "FF-PSI-69-CHK-01" in res["citations"]

def test_rag_connector_raises_on_http_error():
    """B4: التأكد من أن الموصل يثير Exception صريح عند فشل الاتصال ولا يبتلع الأخطاء."""
    connector = RAGConnector(mode="api", api_base_url="http://127.0.0.1:9998")  # بورت غير متاح
    with pytest.raises(RuntimeError) as exc_info:
        connector.query("اختبار استعلام يفشل")
    assert "فشل استدعاء" in str(exc_info.value)
