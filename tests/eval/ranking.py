from typing import List, Dict, Any, Optional

def rank_models(
    candidates: List[Dict[str, Any]],
    min_recall: float = 0.70,
    min_faithfulness: float = 0.80,
    max_hallucination_rate: float = 0.05
) -> List[Dict[str, Any]]:
    """
    Workstream C6: ترشيح وترتيب النماذج اللغوية (LLM/RAG Models) متعدد المعايير.
    يستبعد أي نموذج يفشل في متطلبات الأمان أو العتبات الدنيا (Hard Gate)،
    ثم يرتب الباقي بناءً على كفاءة Pareto (الدقة العلمية مقابل زمن الاستجابة).
    """
    eligible = []
    for m in candidates:
        # استبعاد النماذج غير المطابقة للأمان العلمي
        if m.get("hallucination_rate", 1.0) > max_hallucination_rate:
            continue
        if m.get("recall_at_5", 0.0) < min_recall:
            continue
        if m.get("faithfulness", 0.0) < min_faithfulness:
            continue

        # احتساب درجة الجدارة المجمعة (Composite Scientific Score)
        # 40% Recall, 40% Faithfulness, 20% زمن استجابة مقلوب
        lat = max(m.get("latency_p95_ms", 1000.0), 10.0)
        speed_score = min(1000.0 / lat, 1.0)
        composite = (
            0.40 * m.get("recall_at_5", 0.0) +
            0.40 * m.get("faithfulness", 0.0) +
            0.20 * speed_score
        )
        scored_m = dict(m)
        scored_m["composite_score"] = round(composite, 4)
        eligible.append(scored_m)

    # ترتيب تنازلي بناءً على الدرجة
    return sorted(eligible, key=lambda x: x["composite_score"], reverse=True)


def rank_documents(
    documents: List[Dict[str, Any]],
    dense_weight: float = 0.6,
    lexical_weight: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Workstream C6 & B5: ترتيب الوثائق المسترجعة هجيناً (Hybrid Scoring).
    يجمع بين تشابه المتجهات الكثيفة (Dense) وتطابق الكلمات المفتاحية (BM25 Lexical).
    """
    scored_docs = []
    for doc in documents:
        d_score = doc.get("dense_score", 0.0)
        l_score = doc.get("lexical_score", 0.0)
        auth_boost = 1.1 if "NASA-TM" in doc.get("locator", "") or "NIST" in doc.get("locator", "") else 1.0

        hybrid_score = (dense_weight * d_score + lexical_weight * l_score) * auth_boost
        d_copy = dict(doc)
        d_copy["hybrid_score"] = round(hybrid_score, 4)
        scored_docs.append(d_copy)

    return sorted(scored_docs, key=lambda x: x["hybrid_score"], reverse=True)


def rank_evidence(
    evidence_items: List[Dict[str, Any]],
    required_keywords: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    ترتيب الأدلة المستخلصة بحسب الصلة المباشرة بالمقطع والمصدر الموثق.
    """
    def score_item(item):
        base = item.get("confidence", 0.5)
        text = item.get("text", "").lower()
        if required_keywords:
            matches = sum(1 for kw in required_keywords if kw.lower() in text)
            base += 0.1 * matches
        return base

    return sorted(evidence_items, key=score_item, reverse=True)


def rank_datasets(
    datasets: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    ترتيب مجموعات البيانات بحسب اكتمال التوثيق وحجم العينة وجودة التوسيم (C4).
    """
    def score_ds(ds):
        completeness = ds.get("completeness_rate", 0.0)
        iaa = ds.get("annotator_agreement", 0.0)
        size_factor = min(ds.get("size", 0) / 100.0, 1.0)
        return 0.4 * completeness + 0.4 * iaa + 0.2 * size_factor

    return sorted(datasets, key=score_ds, reverse=True)


def rank_knowledge_records(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    ترتيب السجلات المعرفية (C5) بحسب نوع المصدر ومستوى الإثبات المستقل (Corroboration).
    الأولوية: source-reported > derived > machine-extracted > model-generated > hypothesis
    """
    type_priority = {
        "source-reported": 5,
        "derived": 4,
        "machine-extracted": 3,
        "model-generated": 2,
        "hypothesis": 1
    }

    def score_rec(rec):
        prio = type_priority.get(rec.get("record_type", "hypothesis"), 1)
        corrob_count = rec.get("corroboration_count", 1)
        return prio * 10 + corrob_count

    return sorted(records, key=score_rec, reverse=True)
