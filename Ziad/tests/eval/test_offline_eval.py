import pytest
import socket
from tests.eval.master_pipeline import MasterSafetyPipeline, LLMJudge
from tests.eval.rag_connector import RAGConnector

def test_offline_execution_under_simulated_socket_block(monkeypatch):
    """
    Workstream E5-11: التحقق الصارم من عمل البايبلاين والتقييم في بيئة معزولة تماماً عن الشبكة
    (Simulated Air-Gapped Physical Disconnection).
    """
    # منع أي اتصال شبكي على مستوى نظام التشغيل
    def guard_socket(*args, **kwargs):
        raise OSError("Physical network disconnected: Socket access blocked by Air-Gap protocol.")

    monkeypatch.setattr(socket, "socket", guard_socket)

    # 1. التحقق من عمل محرك التقييم المحلي في غياب النت
    judge = LLMJudge()
    res = judge.evaluate_faithfulness(
        query="ما هي سرعة انتشار اللهب في الجاذبية الصغرى؟",
        retrieved_context="في بيئة الجاذبية الصغرى ينتشر اللهب ببطء.",
        model_answer="ينتشر اللهب في الجاذبية الصغرى بشكل كروي وبطيء."
    )
    assert res["is_hallucination_free"] is True
    assert res["judge_mode"] == "local-fallback"

    # 2. التحقق من تشغيل البايبلاين الكامل أوفلاين
    pipeline = MasterSafetyPipeline()
    pipeline_res = pipeline.process_and_validate(
        query="ما هي إجراءات السلامة؟",
        raw_report="وثيقة NASA-TM-2024-0012: الإجراءات سليمة.",
        visual_features={"anomaly_detected": False},
        model_answer="وفقاً لـ NASA-TM-2024-0012 فإن الإجراءات سليمة.",
        expected_citations=["NASA-TM-2024-0012"]
    )
    assert pipeline_res["final_status"] == "APPROVED"
    assert "provenance" in pipeline_res

def test_rag_connector_offline_mock_mode():
    """التحقق من أن موصل الـ RAG يعمل أوفلاين بدون استدعاءات خارجية."""
    connector = RAGConnector(mode="mock")
    out = connector.query("ما هي خصائص اللهب في الفضاء؟")
    assert "retrieved_doc_ids" in out
    assert len(out["retrieved_doc_ids"]) > 0
