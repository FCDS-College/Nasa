import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure utf-8 encoding for console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = REPO_ROOT / "audit_log.json"

class AuditLogger:
    """نظام تسجيل وتدقيق مركزي يدعم تحديد مسارات ثابتة نسبة لمجلد المشروع."""
    def __init__(self, log_path=None):
        self.log_path = Path(log_path) if log_path else AUDIT_FILE

    def log_security_event(self, test_id, event_type, details):
        logs = []
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except Exception:
                logs = []

        event_record = {
            "log_id": len(logs) + 1,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "test_id": test_id,
            "event_type": event_type,
            "details": details
        }
        logs.append(event_record)

        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=4)

        print(f"🔒 [Audit Log] تم تسجيل الحدث [{event_type}] للحالة {test_id} بنجاح.")
        return event_record

# Backward compatibility functions
_default_logger = AuditLogger()

def log_security_event(test_id, event_type, details):
    return _default_logger.log_security_event(test_id, event_type, details)

if __name__ == "__main__":
    log_security_event(
        test_id="TC_MCG_001",
        event_type="PROVENANCE_CHECK_INIT",
        details="بدء فحص بيانات نسب وتدقيق تجارب الاحتراق في بيئة الجاذبية الصغرى."
    )