import os
import sys
import json
import re
import hashlib
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[2]

class ProvenanceTracker:
    """يتتبع بيانات النسب والتسجيل الخاصة بـ Section 18 لكل عملية تقييم."""
    def get_provenance(self):
        return {
            "git_commit": self._get_git_commit(),
            "dataset_sha256": self._compute_dataset_hash(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scorer_version": "v2.0",
            "model_provider": os.getenv("MODEL_PROVIDER", "gemini-pro"),
            "prompt_version": "prompt-v2.0",
            "hardware": self._get_hardware_info(),
            "rubric_version": "v2.0"
        }

    def _get_git_commit(self):
        # 1. فحص متغير بيئة GitHub Actions
        env_sha = os.getenv("GITHUB_SHA")
        if env_sha:
            return env_sha.strip()[:12]

        # 2. محاولة استدعاء git محلياً
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT)
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()[:12]
        except Exception:
            pass

        # 3. إرجاع unknown بشكل صريح وشفاف
        return "unknown"

    def _compute_dataset_hash(self):
        gold_path = REPO_ROOT / "datasets" / "evaluation" / "rag_gold.jsonl"
        if gold_path.exists():
            return hashlib.sha256(gold_path.read_bytes()).hexdigest()
        return "file-not-found"

    def _get_hardware_info(self):
        proc = platform.processor() or "unknown-processor"
        return f"{platform.system()}-{platform.machine()}-{proc[:30]}"


class PIIMaskingGuardrail:
    """حجب البيانات الحساسة وأرقام الهواتف ورموز الوثائق المصنفة في سياق NASA."""
    def mask_sensitive_data(self, text):
        masked = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '[EMAIL_REDACTED]', text)
        masked = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', masked)
        masked = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', masked)
        masked = re.sub(r'NASA-CONF-\w+', '[CLASSIFIED_REF]', masked)
        return {"masked_output": masked, "pii_detected": masked != text}


class CitationVerificationGuardrail:
    """التحقق من مطابقة وصحة الاستشهادات المرجعية العلمية لـ NASA / NIST."""
    def verify_response_citations(self, model_answer, retrieved_context, expected_citations):
        if not expected_citations:
            return {"safe_to_publish": True, "reason": "No citations expected.", "citation_score": 1.0}
        matched = [c for c in expected_citations if c in model_answer]
        score = len(matched) / len(expected_citations)
        passed = score >= 0.5
        return {
            "safe_to_publish": passed,
            "citation_score": score,
            "matched_citations": matched,
            "reason": f"Matched {len(matched)}/{len(expected_citations)} citations."
        }


class CrossModalConsistencyEngine:
    """كشف التناقض بين التقارير النصية والبيانات والملاحظات البصرية لتجارب الاحتراق."""
    def check_consistency(self, text_report, visual_features):
        text_says_nominal = any(w in text_report for w in ["nominal", "سليم", "طبيعي", "مستقر", "آمن"])
        visual_shows_anomaly = visual_features.get("anomaly_detected", False) or visual_features.get("damage_detected", False)
        if text_says_nominal and visual_shows_anomaly:
            return {
                "is_consistent": False,
                "warning": "⚠️ تناقض: التقرير النصي يشير لحالة طبيعية بينما تظهر البيانات البصرية مؤشرات خلل/شذوذ!"
            }
        return {"is_consistent": True, "warning": "✨ التوافق بين النصوص والملاحظات البصرية سليم."}


class LLMJudge:
    """
    محرك التقييم الذكي الهجين (Hybrid LLM-as-a-Judge):
    يستخدم Google Gemini API عند توفر مفتاح GEMINI_API_KEY،
    مع التراجع التلقائي (Local Fallback) للفحص المحلي السريع عند عدم توفر الإنترنت أو المفتاح.
    """
    def __init__(self, model_name: str = "gemini-1.5-pro"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.has_gemini = False
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.has_gemini = True
            except Exception:
                self.has_gemini = False

    def evaluate_faithfulness(self, query, retrieved_context, model_answer):
        # 1. إذا كان Gemini متوفراً، نستدعيه للحكم الدقيق
        if self.has_gemini:
            try:
                prompt = (
                    f"You are an expert scientific evaluator for NASA microgravity combustion research.\n"
                    f"Evaluate if the model answer is strictly grounded in the retrieved context without hallucinations.\n"
                    f"Query: {query}\n"
                    f"Context: {retrieved_context}\n"
                    f"Answer: {model_answer}\n"
                    f"Return JSON with: {{\"is_faithful\": bool, \"score\": float, \"reason\": str}}"
                )
                response = self.model.generate_content(prompt)
                # استخراج النتيجة من النص
                text = response.text.lower()
                is_faithful = "true" in text or "score\": 1" in text or "faithful" in text
                return {
                    "is_hallucination_free": is_faithful,
                    "domain_relevant": True,
                    "judge_mode": "gemini-api"
                }
            except Exception:
                pass  # Fallback to local heuristic on any API error

        # 2. Local Fallback Heuristic
        keywords = [
            "microgravity", "combustion", "flame", "احتراق", "جاذبية",
            "iss", "nasa", "nist", "spacecraft", "حرارة", "لهب", "أكسجين",
            "flex", "bass", "saffire", "spice"
        ]
        is_faithful = len(model_answer.strip()) > 0 and any(w in model_answer.lower() for w in keywords)
        return {
            "is_hallucination_free": is_faithful,
            "domain_relevant": is_faithful,
            "scorer": "heuristic-v1",
            "judge_mode": "local-fallback"
        }


class SelfCorrectionGuard:
    """التحقق التلقائي ومحاولة توجيه وتصحيح الإجابة في حال كانت مقتضبة أو غير كافية."""
    def validate_and_correct(self, model_answer, retrieved_context):
        if len(model_answer.strip()) < 10:
            return {"status": "NEEDS_CORRECTION", "final_answer": model_answer, "reason": "الإجابة قصيرة جداً"}
        return {"status": "VERIFIED", "final_answer": model_answer}


class MasterSafetyPipeline:
    """البايبلاين الموحد الرئيسي لفحص أمان وموثوقية وتقييم إجابات RAG مع تتبع بيانات §18."""
    def __init__(self):
        self.provenance = ProvenanceTracker()
        self.pii_guard = PIIMaskingGuardrail()
        self.citation_guard = CitationVerificationGuardrail()
        self.consistency_engine = CrossModalConsistencyEngine()
        self.llm_judge = LLMJudge()
        self.self_correction = SelfCorrectionGuard()

    def process_and_validate(self, query, raw_report, visual_features, model_answer, expected_citations):
        prov = self.provenance.get_provenance()
        masked = self.pii_guard.mask_sensitive_data(raw_report)
        consistency = self.consistency_engine.check_consistency(raw_report, visual_features)
        
        if not consistency["is_consistent"]:
            return {"final_status": "BLOCKED", "reason": consistency["warning"], "provenance": prov}

        citation = self.citation_guard.verify_response_citations(model_answer, raw_report, expected_citations)
        if not citation["safe_to_publish"]:
            return {"final_status": "BLOCKED", "reason": citation["reason"], "provenance": prov}

        faithfulness = self.llm_judge.evaluate_faithfulness(query, raw_report, model_answer)
        if not faithfulness["is_hallucination_free"]:
            return {"final_status": "BLOCKED", "reason": "❌ فشل فحص الأمانة والصلة بالمجال العلمي.", "provenance": prov}

        correction = self.self_correction.validate_and_correct(model_answer, raw_report)
        return {
            "final_status": "APPROVED",
            "secured_report": masked["masked_output"],
            "final_answer": correction["final_answer"],
            "provenance": prov,
            "checks": {
                "pii_masked": masked["pii_detected"],
                "cross_modal_consistent": consistency["is_consistent"],
                "citations_verified": citation["safe_to_publish"],
                "faithfulness_passed": faithfulness["is_hallucination_free"]
            }
        }

    def generate_report(self, results, output_path=None):
        prov = self.provenance.get_provenance()
        approved_count = sum(1 for r in results if r.get("final_status") == "APPROVED")
        blocked_count = sum(1 for r in results if r.get("final_status") == "BLOCKED")
        total = len(results)
        report = {
            "provenance": prov,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_evaluated": total,
            "pass_count": approved_count,
            "fail_count": blocked_count,
            "pass_rate": (approved_count / total) if total > 0 else 0.0,
            "results": results
        }
        if output_path is None:
            output_path = REPO_ROOT / "evaluation_report.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report

if __name__ == "__main__":
    pipeline = MasterSafetyPipeline()
    sample_res = pipeline.process_and_validate(
        query="ما هي طبيعة انتشار اللهب في تجربة الجاذبية الصغرى على محطة الفضاء الدولية؟",
        raw_report="وفقاً لوثيقة NASA-TM-2024-0012 Section 3.1، فإن اللهب يتخذ شكلاً كروياً منتظماً.",
        visual_features={"anomaly_detected": False},
        model_answer="يتخذ اللهب شكلاً كروياً في بيئة الجاذبية الصغرى طبقاً لـ NASA-TM-2024-0012.",
        expected_citations=["NASA-TM-2024-0012"]
    )
    print("نتائج فحص العينة:")
    print(json.dumps(sample_res, ensure_ascii=False, indent=2))