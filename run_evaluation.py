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
    n_unanswerable = 0

    for idx, case in enumerate(cases, 1):
        q = case["query"]
        expected_ids = case.get("expected_evidence_ids", [])

        # استدعاء نموذج الـ RAG عبر الـ Connector الموحد
        rag_output = rag_client.query(q, top_k=5)

        # حساب مقاييس الاسترجاع
        r_k = compute_recall_at_k(rag_output["retrieved_doc_ids"], expected_ids, k=5)
        mrr = compute_mrr(rag_output["retrieved_doc_ids"], expected_ids)
        cit_res = compute_citation_metrics(rag_output["citations"], expected_ids)

        # Retrieval recall/MRR are undefined (None) for cases that expect no evidence; they are not averaged.
        # Citation F1 is likewise averaged over answerable cases only: crediting "cited nothing" on an
        # unanswerable case is an abstention signal, not citation quality.
        if r_k is None:
            n_unanswerable += 1
        else:
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
            "retrieval_recall@5": None if r_k is None else round(r_k, 3),
            "mrr": None if mrr is None else round(mrr, 3),
            "citation_f1": round(cit_res["f1"], 3),
            "safety_status": eval_res["final_status"]
        })

    # إحصائيات عامة
    avg_recall = sum(recalls) / len(recalls) if recalls else None
    avg_mrr = sum(mrrs) / len(mrrs) if mrrs else None
    avg_cit_f1 = sum(citation_f1s) / len(citation_f1s) if citation_f1s else None

    provenance = pipeline.provenance.get_provenance()

    mock = model_mode.lower() == "mock"
    final_report = {
        "evaluated_system": {
            "kind": model_mode.lower(),
            "note": ("Hard-coded outputs of tests/eval/mock_rag.py: this scores the evaluation harness, not Flame."
                     if mock else "Live system."),
        },
        "caveats": [
            "Abstention correctness on unanswerable cases is not computed.",
            "Evidence IDs in rag_gold.jsonl (e.g. DOC-001-P15) are not documents of the indexed corpus.",
            "Means are over answerable cases only; there are no confidence intervals.",
        ],
        "provenance": provenance,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(cases),
        "pass_count": sum(1 for r in results if r["safety_status"] == "APPROVED"),
        "fail_count": sum(1 for r in results if r["safety_status"] == "BLOCKED"),
        "metrics_summary": {
            "n_answerable": len(recalls),
            "n_unanswerable": n_unanswerable,
            "mean_recall@5": None if avg_recall is None else round(avg_recall, 4),
            "mean_mrr": None if avg_mrr is None else round(avg_mrr, 4),
            "mean_citation_f1": None if avg_cit_f1 is None else round(avg_cit_f1, 4)
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
    def pct(value):
        return "n/a (no answerable case)" if value is None else f"{value:.2%}"

    print(f"⚠️  Evaluated system: {final_report['evaluated_system']['kind'].upper()}. {final_report['evaluated_system']['note']}")
    print(f"🎯 Mean Recall@5:        {pct(avg_recall)}  (over {len(recalls)} answerable cases)")
    print(f"🎯 Mean MRR:             {pct(avg_mrr)}")
    print(f"🎯 Mean Citation F1:     {pct(avg_cit_f1)}")
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
