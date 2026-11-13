import json
import sys
from pathlib import Path

# Ensure utf-8 encoding for console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE_PATH = REPO_ROOT / "datasets" / "evaluation" / "rag_gold.jsonl"

BASELINE_THRESHOLDS = {
    "retrieval_relevance": 4.0,
    "faithfulness": 4.5,
    "citation_accuracy": 4.0
}

def load_test_cases(file_path=None):
    """قراءة ملف الحالات وتجهيزه في صيغة DataFrame مع التكيف مع أي بنية حقول."""
    import pandas as pd   # only loading needs pandas; evaluate_model works on any frame-like object (CI does not install pandas)

    path = Path(file_path) if file_path else DEFAULT_FILE_PATH
    if not path.exists():
        print(f"❌ لم يتم العثور على الملف: {path}")
        return pd.DataFrame()

    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    df = pd.json_normalize(data)
    return df

def evaluate_model(df):
    """حساب متوسط الدرجات والمقارنة مع الحدود الدنيا المعتمدة (Baselines)."""
    print("=" * 40)
    print(" AI System Evaluation Report (NASA MVP) ")
    print("=" * 40)

    if df.empty:
        print("⚠️ لا توجد بيانات للتقييم.")
        return False

    metrics_cols = [
        'metrics.retrieval_relevance',
        'metrics.faithfulness',
        'metrics.citation_accuracy'
    ]

    all_passed = True
    found_metrics = False

    for col in metrics_cols:
        if col not in df.columns:
            continue
        found_metrics = True
        metric_name = col.split('.')[1]
        mean_score = df[col].mean()
        threshold = BASELINE_THRESHOLDS.get(metric_name, 4.0)

        status = "✅ PASS" if mean_score >= threshold else "❌ FAIL"
        if mean_score < threshold:
            all_passed = False

        print(f"Metric: {metric_name.replace('_', ' ').title()}")
        print(f"  - Average: {mean_score:.2f} / 5.0")
        print(f"  - Required minimum: {threshold}")
        print(f"  - Status: {status}\n")

    if not found_metrics:
        # A gold-case file has questions and expected evidence, not scores from a system. Nothing was measured, so
        # reporting "passed" (as this used to) is a false claim.
        print("⚠️ NOT EVALUATED: the data file has no `metrics.*` score columns (it holds gold cases, not system outputs).")
        print("   لم يتم التقييم: الملف لا يحتوي على درجات نظام. لا يمكن اعتبار النتيجة نجاحاً.")
        print("=" * 40)
        return False

    print("=" * 40)
    if all_passed:
        print("🎉 Final result: The system passed the baseline!")
    else:
        print("⚠️ Final result: The system needs improvement before approval.")
    print("=" * 40)

    return all_passed

if __name__ == "__main__":
    df_results = load_test_cases()
    passed = evaluate_model(df_results)
    sys.exit(0 if passed else 1)