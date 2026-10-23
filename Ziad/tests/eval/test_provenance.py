import os
import json
import pytest
from pathlib import Path
import jsonschema

# Anchor path strictly to the repository root
REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_DATASET_PATH = REPO_ROOT / "datasets" / "evaluation" / "rag_gold.jsonl"
GOLD_SCHEMA_PATH = REPO_ROOT / "datasets" / "evaluation" / "gold_schema.json"
CHECKLIST_PATH = REPO_ROOT / "docs" / "evaluation" / "provenance_checklist.md"

def test_gold_dataset_exists():
    """التحقق من وجود ملف الـ Gold Dataset في المسار المحدد بالنسبة للـ repo root"""
    assert GOLD_DATASET_PATH.exists(), f"❌ خطأ: ملف الـ Gold Dataset غير موجود في المسار {GOLD_DATASET_PATH}"

def test_schema_file_exists():
    """التحقق من وجود ملف مخطط JSON Schema"""
    assert GOLD_SCHEMA_PATH.exists(), f"❌ خطأ: ملف المخطط غير موجود في المسار {GOLD_SCHEMA_PATH}"

def test_provenance_checklist_exists():
    """التحقق من وجود قائمة تدقيق تتبع البيانات (Provenance Checklist)"""
    assert CHECKLIST_PATH.exists(), f"❌ خطأ: ملف قائمة التدقيق غير موجود في المسار {CHECKLIST_PATH}"

def test_gold_schema_compliance_and_uniqueness():
    """التحقق من مطابقة جميع الحالات لمخطط §18 (id, expected_evidence_ids, source_scope) وخلوها من التكرار."""
    with open(GOLD_SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    case_ids = set()
    queries = set()
    cases = []

    with open(GOLD_DATASET_PATH, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            case = json.loads(line_str)
            # التحقق عبر jsonschema
            jsonschema.validate(instance=case, schema=schema)

            # التحقق من تفرد المعرف id (§18 standard)
            cid = case["id"]
            assert cid not in case_ids, f"❌ تكرار في معرف الحالة في السطر {idx}: {cid}"
            case_ids.add(cid)

            # التحقق من عدم تكرار الأسئلة
            q = case["query"].strip()
            assert q not in queries, f"❌ تكرار في نص السؤال: {q}"
            queries.add(q)

            # التحقق من حقول B1 للمستندات القابلة للإجابة: author, reviewer, source_id
            if case.get("answerable"):
                for ev in case.get("expected_evidence", []):
                    assert "source_id" in ev, f"❌ missing source_id in evidence for {cid}"
                    assert "author" in ev, f"❌ missing author in evidence for {cid}"
                    assert "reviewer" in ev, f"❌ missing reviewer in evidence for {cid}"
                    assert len(ev.get("text", "").strip()) > 5, f"❌ empty evidence text for {cid}"

            cases.append(case)

    # التحقق من الحد الأدنى للحالات (30 حالة على الأقل)
    assert len(cases) >= 30, f"⚠️ عدد الحالات الحالي هو {len(cases)} والمطلوب 30 حالة على الأقل."

def test_dataset_coverage_metrics():
    """التحقق من تغطية أنواع الوسائط ومستويات الصعوبة وحالات عدم الإجابة والحقن المعادي"""
    cases = []
    with open(GOLD_DATASET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    splits = {c.get("split") for c in cases}
    modalities = {c.get("modality") for c in cases}
    difficulties = {c.get("difficulty") for c in cases}

    assert {"dev", "validation", "holdout"}.issubset(splits), "❌ يجب تغطية التقسيمات الثلاثة (dev, validation, holdout)"
    assert {"text", "image", "table"}.issubset(modalities), "❌ يجب تغطية الوسائط الأساسية (text, image, table)"
    assert {"easy", "medium", "hard"}.issubset(difficulties), "❌ يجب تغطية مستويات الصعوبة المختلفة"

    unanswerable = [c for c in cases if not c.get("answerable", True)]
    assert len(unanswerable) >= 3, "⚠️ يجب وجود 3 حالات على الأقل بنظام لا يوجد إجابة (No Answer)."

    adversarial = [c for c in cases if c.get("category") == "adversarial"]
    assert len(adversarial) >= 3, "⚠️ يجب وجود 3 حالات على الأقل لاختبار مقاومة الحقن (Adversarial/Prompt-injection)."

def test_no_document_leakage():
    """التأكد الصارم من عدم تسرب معرفات الأدلة بين مجموعات التدريب والتأكيد والاختبار النهائي (Zero Leakage)."""
    split_evidence = {"dev": set(), "validation": set(), "holdout": set()}
    with open(GOLD_DATASET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                case = json.loads(line)
                split = case.get("split")
                if split in split_evidence:
                    for ev_id in case.get("expected_evidence_ids", []):
                        split_evidence[split].add(ev_id)

    # منع تداخل الوثائق/الأدلة
    dev_val_leak = split_evidence["dev"].intersection(split_evidence["validation"])
    dev_hold_leak = split_evidence["dev"].intersection(split_evidence["holdout"])
    val_hold_leak = split_evidence["validation"].intersection(split_evidence["holdout"])

    assert not dev_val_leak, f"❌ تسرب أدلة بين dev و validation: {dev_val_leak}"
    assert not dev_hold_leak, f"❌ تسرب أدلة بين dev و holdout: {dev_hold_leak}"
    assert not val_hold_leak, f"❌ تسرب أدلة بين validation و holdout: {val_hold_leak}"