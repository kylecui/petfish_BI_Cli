from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from threading import Lock

from petfish_bi_cli.compliance.checker import redact_pii

AUDIT_LOG_PATH = Path("outputs/audit/audit.jsonl")


class AuditLogger:
    def __init__(self, log_path: Path | None = None):
        self._path = log_path or AUDIT_LOG_PATH
        self._lock = Lock()

    def log(
        self,
        api_key: str | None,
        query: str,
        status: str,
        response_time_s: float,
        session_id: str | None = None,
        error: str | None = None,
    ) -> None:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "api_key_hash": self._hash_key(api_key) if api_key else "anonymous",
            "query": redact_pii(query),
            "status": status,
            "response_time_s": round(response_time_s, 3),
            "session_id": session_id,
            "error": error,
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _hash_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]


_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _audit_logger
