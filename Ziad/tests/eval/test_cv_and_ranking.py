import numpy as np
import pytest
from tests.eval.cv_metrics import (
    compute_mask_iou,
    compute_dice_coefficient,
    compute_precision_recall_masks
)
from tests.eval.ranking import (
    rank_models,
    rank_documents,
    rank_evidence,
    rank_knowledge_records,
    rank_datasets
)

def test_cv_iou_and_dice_perfect_overlap():
    """التحقق من حساب IoU و Dice عند التطابق التام للأقنعة (1.0)."""
    mask1 = np.ones((50, 50), dtype=np.uint8)
    mask2 = np.ones((50, 50), dtype=np.uint8)

    assert compute_mask_iou(mask1, mask2) == 1.0
    assert compute_dice_coefficient(mask1, mask2) == 1.0

def test_cv_iou_half_overlap():
    """التحقق من حساب IoU و Dice عند التداخل الجزئي للأقنعة."""
    mask_a = np.zeros((10, 10), dtype=np.uint8)
    mask_b = np.zeros((10, 10), dtype=np.uint8)

    # 4 بكسل متداخلة
    mask_a[:2, :2] = 1 # 4 pixels
    mask_b[:2, 1:3] = 1 # 4 pixels, overlap is 2 pixels
    # intersection = 2, union = 6 -> IoU = 2/6 = 0.333
    iou = compute_mask_iou(mask_a, mask_b)
    assert round(iou, 2) == 0.33

def test_rank_models_hard_gate_elimination():
    """التحقق من استبعاد النماذج ذات معدل الهلوسة المرتفع أو الاستدعاء المنخفض."""
    candidates = [
        {"name": "Hallucinating-Model", "hallucination_rate": 0.08, "recall_at_5": 0.90, "faithfulness": 0.90, "latency_p95_ms": 100},
        {"name": "Low-Recall-Model", "hallucination_rate": 0.01, "recall_at_5": 0.50, "faithfulness": 0.90, "latency_p95_ms": 120},
        {"name": "Valid-Model-A", "hallucination_rate": 0.02, "recall_at_5": 0.85, "faithfulness": 0.88, "latency_p95_ms": 200},
        {"name": "Valid-Model-B", "hallucination_rate": 0.01, "recall_at_5": 0.92, "faithfulness": 0.95, "latency_p95_ms": 150}
    ]

    ranked = rank_models(candidates, min_recall=0.70, max_hallucination_rate=0.05)
    # يجب استبعاد أول نموذجين
    assert len(ranked) == 2
    assert ranked[0]["name"] == "Valid-Model-B"
    assert ranked[1]["name"] == "Valid-Model-A"

def test_rank_documents_hybrid_authority_boost():
    """التحقق من تأثير الترتيب الهجين وتعزيز وثائق NASA-TM المعتمدة."""
    docs = [
        {"id": "doc1", "dense_score": 0.8, "lexical_score": 0.7, "locator": "Standard-Report-1"},
        {"id": "doc2", "dense_score": 0.8, "lexical_score": 0.7, "locator": "NASA-TM-2024-0012"}
    ]
    ranked = rank_documents(docs)
    # doc2 يجب أن يتصدر بسبب تعزيز NASA-TM
    assert ranked[0]["id"] == "doc2"
    assert ranked[0]["hybrid_score"] > ranked[1]["hybrid_score"]

def test_rank_knowledge_records_hierarchy():
    """التحقق من أولوية السجلات الموثقة (source-reported) على المستخلصة آلياً."""
    records = [
        {"id": "rec_auto", "record_type": "machine-extracted", "corroboration_count": 5},
        {"id": "rec_source", "record_type": "source-reported", "corroboration_count": 1},
        {"id": "rec_hypo", "record_type": "hypothesis", "corroboration_count": 0}
    ]
    ranked = rank_knowledge_records(records)
    assert ranked[0]["id"] == "rec_source"
    assert ranked[1]["id"] == "rec_auto"
    assert ranked[2]["id"] == "rec_hypo"
