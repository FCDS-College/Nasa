import numpy as np
from typing import Dict, List, Optional

def compute_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int = 5) -> Optional[float]:
    """
    حساب Recall@k: نسبة الوثائق المسترجعة ذات الصلة ضمن أول k نتائج.
    """
    if not expected_ids:
        # No evidence is expected (an unanswerable case): retrieval recall is undefined, not perfect.
        # Returning 1.0 here let unanswerable cases inflate the reported mean. Callers skip None.
        return None
    
    top_k = set(retrieved_ids[:k])
    expected_set = set(expected_ids)
    hits = top_k.intersection(expected_set)
    return len(hits) / len(expected_set)

def compute_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> Optional[float]:
    """
    حساب Mean Reciprocal Rank (MRR): مقلوب رتبة أول وثيقة صحيحة تظهر في النتائج.
    """
    if not expected_ids:
        return None  # undefined for an unanswerable case; see compute_recall_at_k
    
    expected_set = set(expected_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in expected_set:
            return 1.0 / rank
    return 0.0

def compute_ndcg_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int = 5) -> Optional[float]:
    """
    حساب Normalized Discounted Cumulative Gain (nDCG@k) بثنائية الصلة (Binary relevance).
    """
    if not expected_ids:
        return None  # undefined for an unanswerable case; see compute_recall_at_k
    
    expected_set = set(expected_ids)
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in expected_set:
            dcg += 1.0 / np.log2(i + 2)  # i+2 لأن log2(1) = 0
            
    # حساب المثالي Ideal DCG
    ideal_hits = min(len(expected_ids), k)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_hits))
    
    if idcg == 0.0:
        return 0.0
    return dcg / idcg

def compute_citation_metrics(cited_ids: List[str], expected_ids: List[str]) -> Dict[str, float]:
    """
    حساب دقة واستدعاء الاستشهادات (Citation Precision & Recall).
    """
    if not expected_ids and not cited_ids:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not cited_ids:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not expected_ids:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    cited_set = set(cited_ids)
    expected_set = set(expected_ids)
    true_positives = len(cited_set.intersection(expected_set))

    precision = true_positives / len(cited_set)
    recall = true_positives / len(expected_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }
