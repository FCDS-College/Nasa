import pytest
from pathlib import Path
from tests.eval.master_pipeline import (
    ProvenanceTracker,
    PIIMaskingGuardrail,
    CitationVerificationGuardrail,
    CrossModalConsistencyEngine,
    LLMJudge,
    MasterSafetyPipeline
)

REPO_ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture
def pipeline():
    return MasterSafetyPipeline()

def test_provenance_tracker_fields():
    """التحقق من احتواء كائن التتبع على كافة حقول الفقرة 18 (Section 18)."""
    tracker = ProvenanceTracker()
    prov = tracker.get_provenance()
    required_keys = [
        "git_commit", "dataset_sha256", "timestamp",
        "scorer_version", "model_provider", "prompt_version",
        "hardware", "rubric_version"
    ]
    for key in required_keys:
        assert key in prov, f"❌ حقل مفقود في تتبع النسب: {key}"
    assert prov["scorer_version"] == "v2.0"
    assert prov["rubric_version"] == "v2.0"

def test_pii_masking_nasa_context():
    """التحقق من حجب المعرفات والبريد الإلكتروني وأرقام الهواتف السرية."""
    guard = PIIMaskingGuardrail()
    text = "يرجى مراجعة الباحث john.doe@nasa.gov أو الوثيقة NASA-CONF-9921 للتحقق."
    res = guard.mask_sensitive_data(text)
    assert res["pii_detected"] is True
    assert "john.doe@nasa.gov" not in res["masked_output"]
    assert "[EMAIL_REDACTED]" in res["masked_output"]
    assert "[CLASSIFIED_REF]" in res["masked_output"]

def test_citation_verification_threshold():
    """التحقق من احتساب وتمرير الاستشهادات المطابقة للمراجع."""
    guard = CitationVerificationGuardrail()
    # حالة نجاح الاستشهاد
    res_pass = guard.verify_response_citations(
        model_answer="وفقاً لـ NASA-TM-2024-0012 فإن اللهب كروي.",
        retrieved_context="",
        expected_citations=["NASA-TM-2024-0012"]
    )
    assert res_pass["safe_to_publish"] is True
    assert res_pass["citation_score"] == 1.0

    # حالة فشل الاستشهاد
    res_fail = guard.verify_response_citations(
        model_answer="اللهب كروي بدون ذكر مصادر.",
        retrieved_context="",
        expected_citations=["NASA-TM-2024-0012", "NIST-SP-1200"]
    )
    assert res_fail["safe_to_publish"] is False
    assert res_fail["citation_score"] == 0.0

def test_cross_modal_inconsistency_detection():
    """التحقق من كشف التضارب بين التقرير النصي والبيانات البصرية."""
    engine = CrossModalConsistencyEngine()
    # حالة التضارب
    res_conflict = engine.check_consistency(
        text_report="الوضع سليم ومستقر تماماً في غرفة الاحتراق.",
        visual_features={"anomaly_detected": True}
    )
    assert res_conflict["is_consistent"] is False

    # حالة التوافق
    res_ok = engine.check_consistency(
        text_report="الوضع طبيعي ومستقر.",
        visual_features={"anomaly_detected": False}
    )
    assert res_ok["is_consistent"] is True

def test_llm_judge_domain_faithfulness():
    """التحقق من تمييز الإجابات ذات الصلة بالمجال العلمي مقابل الإجابات الشاردة."""
    judge = LLMJudge()
    eval_domain = judge.evaluate_faithfulness(
        query="سؤال حول الاحتراق",
        retrieved_context="",
        model_answer="تحدث ظاهرة احتراق الوقود في الجاذبية الصغرى ببطء."
    )
    assert eval_domain["is_hallucination_free"] is True

    eval_out_of_domain = judge.evaluate_faithfulness(
        query="سؤال حول الاحتراق",
        retrieved_context="",
        model_answer="أسعار الأسهم في البورصة ارتفعت اليوم."
    )
    assert eval_out_of_domain["is_hallucination_free"] is False

def test_master_pipeline_end_to_end(pipeline, tmp_path):
    """اختبار مسار الحماية والتقييم المتكامل وإنشاء التقرير المحتوي على بيانات التتبع."""
    query = "كيف يتشكل اللهب في الفضاء؟"
    report = "وثيقة NASA-TM-2024-0012: اللهب كروي ومستقر."
    ans = "طبقاً لـ NASA-TM-2024-0012 يتشكل اللهب كروياً في الفضاء."
    res = pipeline.process_and_validate(
        query=query,
        raw_report=report,
        visual_features={"anomaly_detected": False},
        model_answer=ans,
        expected_citations=["NASA-TM-2024-0012"]
    )
    assert res["final_status"] == "APPROVED"
    assert "provenance" in res

    # اختبار توليد ملف التقرير
    test_rep_file = tmp_path / "test_report.json"
    rep_obj = pipeline.generate_report([res], output_path=test_rep_file)
    assert rep_obj["pass_rate"] == 1.0
    assert rep_obj["total_evaluated"] == 1
    assert "provenance" in rep_obj
    assert test_rep_file.exists()
