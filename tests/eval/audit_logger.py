import json
import os
from datetime import datetime

AUDIT_FILE = "audit_log.json"

def log_security_event(test_id, event_type, details):
    """تسجيل أحداث الحماية، الحظر، أو الأخطاء البصرية في سجل التدقيق المركزي"""
    logs = []
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

    event_record = {
        "log_id": len(logs) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_id": test_id,
        "event_type": event_type,  # مثل: BLOCKED_CITATION, MISSING_VISUAL, SUCCESS
        "details": details
    }
    
    logs.append(event_record)

    with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)
    
    print(f"🔒 [Audit Log] تم تسجيل الحدث [{event_type}] للاختبار {test_id} بنجاح.")

if __name__ == "__main__":
    # تجربة تسجيل حدث حظر بسبب فشل الاستشهاد
    log_security_event(
        test_id="TC_005",
        event_type="BLOCKED_CITATION",
        details="تم حظر الإجابة لخلوها من الاستشهادات المرجعية الصحيحة."
    )