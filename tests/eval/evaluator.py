import json
import pandas as pd

BASELINE_THRESHOLDS = {
    "retrieval_relevance": 4.0,
    "faithfulness": 4.5, # A strict threshold to reduce hallucinations
    "citation_accuracy": 4.0
}


file_path = "test_cases.jsonl"  

def load_test_cases(file_path):
    """Load a JSONL file and convert it to a Pandas DataFrame."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    
    # Flatten the metrics dictionary into separate columns.
    df = pd.json_normalize(data)
    return df


def evaluate_model(df):
    """Calculate average evaluation scores and compare them with the baseline."""
    print("="*40)
    print(" AI System Evaluation Report (MVP) ")
    print("="*40)
    
    # Calculate the average for each metric.
    metrics_cols = ['metrics.retrieval_relevance', 'metrics.faithfulness', 'metrics.citation_accuracy']
    
    all_passed = True
    
    for col in metrics_cols:
        metric_name = col.split('.')[1]
        mean_score = df[col].mean()
        threshold = BASELINE_THRESHOLDS[metric_name]
        
        # Check whether the baseline is met.
        status = "✅ PASS" if mean_score >= threshold else "❌ FAIL"
        if mean_score < threshold:
            all_passed = False
            
        print(f"Metric: {metric_name.replace('_', ' ').title()}")
        print(f"  - Average: {mean_score:.2f} / 5.0")
        print(f"  - Required minimum: {threshold}")
        print(f"  - Status: {status}\n")
    
    print("="*40)
    if all_passed:
        print("🎉 Final result: The system passed the baseline and is ready for the next stage!")
    else:
        print("⚠️ Final result: The system needs improvement before approval.")
    print("="*40)


if __name__ == "__main__":
    # Path to the test cases file.
    file_path = 'test_cases.jsonl'
    
    # Run the evaluation.
    df_results = load_test_cases(file_path)
    evaluate_model(df_results)