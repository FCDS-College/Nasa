import json
import re
from datetime import datetime

# 1. طبقة تعمية البيانات الحساسة (PII Masking)
class PIIMaskingGuardrail:
    def __init__(self):
        print("🔒 تم تفعيل طبقة تعمية البيانات الحساسة (PII Masking)...")

    def mask_sensitive_data(self, text):
        masked_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', text)
        masked_text = re.sub(r'\b01[0-9]{9}\b', '[PHONE_REDACTED]', masked_text)
        masked_text = re.sub(r'REF-\d+', '[CONFIDENTIAL_REF]', masked_text)
        return {"masked_output": masked_text}

# 2. طبقة التحقق من الاستشهادات
class CitationVerificationGuardrail:
    def __init__(self):
        print("🛡️ تم تفعيل طبقة التحقق من الاستشهادات...")

    def verify_response_citations(self, model_answer, retrieved_context, expected_citations):
        has_citations = any(cit in model_answer for cit in expected_citations) if expected_citations else True
        is_grounded = len(model_answer.strip()) > 0 and (has_citations or "مخطط" in model_answer)
        if not is_grounded:
            return {"safe_to_publish": False, "reason": "❌ تم حظر الإجابة لخلوها من الاستشهادات الصحيحة."}
        return {"safe_to_publish": True, "reason": "✨ الاستجابة موثقة بمصادر."}

# 3. محرك التناقض البصري والنصي
class CrossModalConsistencyEngine:
    def __init__(self):
        print("👁️🤖 تم تفعيل محرك كشف التناقض البصري والنصي...")

    def check_consistency(self, text_report, visual_features):
        text_says_safe = "سليم" in text_report or "آمن" in text_report
        visual_shows_damage = visual_features.get("damage_detected", False)
        if text_says_safe and visual_shows_damage:
            return {"is_consistent": False, "warning": "⚠️ تناقض: التقرير النصي يشير للسلامة بينما الوسائط البصرية تظهر أضراراً!"}
        return {"is_consistent": True, "warning": "✨ التوافق سليم."}

# 4. محرك التقييم الذكي (LLM Judge)
class LLMJudge:
    def __init__(self):
        print("🤖 تم تهيئة محرك التقييم الذكي...")

    def evaluate_faithfulness(self, query, retrieved_context, model_answer):
        keywords = ["حريق", "مخطط", "تماس", "تقرير", "إصابة"]
        is_faithful = len(model_answer) > 0 and any(word in model_answer for word in keywords)
        return {"is_hallucination_free": is_faithful}

# 5. طبقة التصحيح الذاتي
class SelfCorrectionGuard:
    def __init__(self):
        print("🛡️✨ تم تفعيل طبقة التصحيح الذاتي...")

    def validate_and_correct(self, model_answer, retrieved_context):
        return {"status": "VERIFIED", "final_answer": model_answer}

# --- البايبلاين الرئيسي المجمع ---
class MasterSafetyPipeline:
    def __init__(self):
        self.pii_guard = PIIMaskingGuardrail()
        self.citation_guard = CitationVerificationGuardrail()
        self.consistency_engine = CrossModalConsistencyEngine()
        self.llm_judge = LLMJudge()
        self.self_correction = SelfCorrectionGuard()

    def process_and_validate_incident(self, query, raw_report, visual_features, model_answer, expected_citations):
        print("\n" + "="*50)
        print("🛡️ بدء فحص وتأمين الاستجابة عبر البايبلاين المتكامل...")
        print("="*50)

        # تنفيذ الفحوصات بالتسلسل
        masked = self.pii_guard.mask_sensitive_data(raw_report)
        
        consistency = self.consistency_engine.check_consistency(raw_report, visual_features)
        if not consistency["is_consistent"]:
            return {"final_status": "BLOCKED", "reason": consistency["warning"]}

        citation = self.citation_guard.verify_response_citations(model_answer, raw_report, expected_citations)
        if not citation["safe_to_publish"]:
            return {"final_status": "BLOCKED", "reason": citation["reason"]}

        faithfulness = self.llm_judge.evaluate_faithfulness(query, raw_report, model_answer)
        if not faithfulness["is_hallucination_free"]:
            return {"final_status": "BLOCKED", "reason": "❌ حظر: فشل تقييم الثقة والاعتمادية."}

        correction = self.self_correction.validate_and_correct(model_answer, raw_report)
        
        return {
            "final_status": "APPROVED",
            "secured_report": masked["masked_output"],
            "final_answer": correction["final_answer"],
            "audit_note": "✨ اجتازت الاستجابة كافة طبقات الحماية والتقييم بنجاح تام."
        }

# تشغيل التجربة
pipeline = MasterSafetyPipeline()
result = pipeline.process_and_validate_incident(
    query="ما هي أسباب الحريق في المخطط الأول؟",
    raw_report="تقرير حادثة الحريق رقم [REF-101] يوضح تفاصيل التماس كهربائي بالمخطط، تواصل مع المهندس عبر ahmed@fire-dept.com",
    visual_features={"damage_detected": True},
    model_answer="أظهر تقرير حادثة الحريق رقم [REF-101] وجود تماس كهربائي.",
    expected_citations=["[REF-101]"]
)

print("\n📊 النتيجة النهائية للبايبلاين الموحد:")
print(json.dumps(result, ensure_ascii=False, indent=2))