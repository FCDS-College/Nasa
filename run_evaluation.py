import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure utf-8 encoding for console output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent
GOLD_DATASET_PATH = REPO_ROOT / "datasets" / "evaluation" / "rag_gold.jsonl"
OUTPUT_REPORT_PATH = REPO_ROOT / "evaluation_report.json"

from tests.eval.master_pipeline import MasterSafetyPipeline
from tests.eval.rag_connector import RAGConnector
from tests.eval.metrics import (
    compute_recall_at_k,
    compute_mrr,
    compute_citation_metrics
)

def run_evaluation_suite(dataset_path: Path, output_path: Path, model_mode: str = "mock", api_url: str = "http://localhost:8000"):
    print("=" * 60)
    print("🚀 بدء دورة التقييم الشاملة لنظام NASA RAG (§18 Evaluation Runner)")
    print("=" * 60)
    print(f"📂 ملف البيانات: {dataset_path.name}")
    print(f"🔌 نمط الموديل (Model Connector): {model_mode.upper()}")

    if not dataset_path.exists():
        print(f"❌ خطأ: لم يتم العثور على ملف البيانات {dataset_path}")
        sys.exit(1)

    pipeline = MasterSafetyPipeline()
    rag_client = RAGConnector(mode=model_mode, api_base_url=api_url)

    cases = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    print(f"📊 إجمالي عدد حالات الاختبار: {len(cases)}")
    print("-" * 60)

    results = []
    recalls = []
    mrrs = []
    citation_f1s = []

    for idx, case in enumerate(cases, 1):
        q = case["query"]
        expected_ids = case.get("expected_evidence_ids", [])

        # استدعاء نموذج الـ RAG عبر الـ Connector الموحد
        rag_output = rag_client.query(q, top_k=5)

        # حساب مقاييس الاسترجاع
        r_k = compute_recall_at_k(rag_output["retrieved_doc_ids"], expected_ids, k=5)
        mrr = compute_mrr(rag_output["retrieved_doc_ids"], expected_ids)
        cit_res = compute_citation_metrics(rag_output["citations"], expected_ids)

        recalls.append(r_k)
        mrrs.append(mrr)
        citation_f1s.append(cit_res["f1"])

        # تشغيل الفحص الأمني عبر البايبلاين
        eval_res = pipeline.process_and_validate(
            query=q,
            raw_report="\n".join(rag_output["retrieved_context"]),
            visual_features={"anomaly_detected": False},
            model_answer=rag_output["answer"],
            expected_citations=[ev["locator"] for ev in case.get("expected_evidence", [])]
        )

        results.append({
            "case_id": case["case_id"],
            "query": q,
            "split": case.get("split"),
            "difficulty": case.get("difficulty"),
            "retrieval_recall@5": round(r_k, 3),
            "mrr": round(mrr, 3),
            "citation_f1": round(cit_res["f1"], 3),
            "safety_status": eval_res["final_status"]
        })

    # إحصائيات عامة
    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0
    avg_cit_f1 = sum(citation_f1s) / len(citation_f1s) if citation_f1s else 0.0

    provenance = pipeline.provenance.get_provenance()

    final_report = {
        "provenance": provenance,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(cases),
        "pass_count": sum(1 for r in results if r["safety_status"] == "APPROVED"),
        "fail_count": sum(1 for r in results if r["safety_status"] == "BLOCKED"),
        "metrics_summary": {
            "mean_recall@5": round(avg_recall, 4),
            "mean_mrr": round(avg_mrr, 4),
            "mean_citation_f1": round(avg_cit_f1, 4)
        },
        "thresholds": {
            "recall@5_target": 0.80,
            "mrr_target": 0.70,
            "citation_f1_target": 0.75
        },
        "detailed_results": results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("📈 ملخص تقرير التقييم الإحصائي (Scorecard Summary):")
    print("=" * 60)
    print(f"🎯 Mean Recall@5:        {avg_recall:.2%}")
    print(f"🎯 Mean MRR:             {avg_mrr:.2%}")
    print(f"🎯 Mean Citation F1:     {avg_cit_f1:.2%}")
    print(f"🔒 الحالات المجتازة أمنياً: {final_report['pass_count']} / {len(cases)}")
    print(f"💾 تم حفظ التقرير في:   {output_path.name}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NASA RAG Evaluation Runner")
    parser.add_argument("--data", type=Path, default=GOLD_DATASET_PATH, help="Path to gold dataset JSONL")
    parser.add_argument("--out", type=Path, default=OUTPUT_REPORT_PATH, help="Path to output report JSON")
    parser.add_argument("--model", type=str, default="mock", choices=["mock", "api"], help="Model connector mode: 'mock' or 'api'")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="Base URL of production RAG API")
    args = parser.parse_args()

    run_evaluation_suite(args.data, args.out, model_mode=args.model, api_url=args.api_url)
