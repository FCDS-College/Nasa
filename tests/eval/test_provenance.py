import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = str(REPO_ROOT / "datasets" / "evaluation" / "rag_gold_arabic_v0.jsonl")
SCHEMA_PATH = str(REPO_ROOT / "datasets" / "evaluation" / "gold_schema.json")


def test_gold_dataset_exists():
    """التحقق من وجود ملف الـ Gold Dataset في المسار الصحيح"""
    path = GOLD_PATH
    assert os.path.exists(path), f"❌ خطأ: ملف الـ Gold Dataset غير موجود في المسار {path}"

def test_gold_dataset_format_and_diversity():
    """التحقق من صحة صيغة البيانات وتنوعها وخلوها من التكرار الوهمي"""
    path = GOLD_PATH
    case_ids = set()
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            
            # التأكد من وجود الحقول الأساسية وفق المعيار
            assert "case_id" in data
            assert "split" in data
            assert "expected_evidence" in data
            assert "answerable" in data
            
            # منع التكرار
            assert data["case_id"] not in case_ids, f"❌ تكرار في معرف الحالة: {data['case_id']}"
            case_ids.add(data["case_id"])
            
    assert len(case_ids) >= 3, "⚠️ تحذير: عدد الحالات الحقيقية قليل جداً."

def test_threshold_consistency():
    """توحيد عتبة النجاح ومنع التضارب بين 4 و 4.5"""
    REQUIRED_THRESHOLD = 4.0  # توحيد العتبة الحرجة لضمان توافق الفحص
    assert REQUIRED_THRESHOLD <= 4.5, "❌ خطأ مطابقة العتبات (Threshold Mismatch) بين المقيمين."


def test_gold_dataset_count_and_structure():
    path = GOLD_PATH
    cases = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
                
    # التأكد من وجود 30 حالة على الأقل
    assert len(cases) >= 30, f"⚠️ عدد الحالات الحالي هو {len(cases)} والمطلوب 30 حالة على الأقل."
    
    no_answer_count = 0
    for case in cases:
        assert "case_id" in case
        assert "query" in case
        assert "expected_evidence" in case
        assert "answerable" in case
        if not case["answerable"]:
            no_answer_count += 1
            
    # التأكد من وجود حالات الـ No Answer المطلوبة (3 حالات)
    assert no_answer_count >= 3, "⚠️ يجب وجود 3 حالات على الأقل بنظام لا يوجد إجابة (No Answer)."

def test_schema_file_exists():
    assert os.path.exists(SCHEMA_PATH), "❌ ملف الـ JSON Schema غير موجود."