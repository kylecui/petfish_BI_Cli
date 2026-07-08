from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEFAULT_SESSION_DIR = Path("outputs/sessions")


class SessionStore:
    def __init__(self, base_dir: Path | None = None):
        self._dir = base_dir or DEFAULT_SESSION_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: Any) -> Path:
        path = self._dir / f"{session.session_id}.json"
        events: list[Any] = []
        emitter = getattr(session, "_emitter", None)
        if emitter is not None:
            raw_events = getattr(emitter, "_events", [])
            events = [e.to_dict() if hasattr(e, "to_dict") else str(e) for e in raw_events]
        data = {
            "session_id": session.session_id,
            "saved_at": time.time(),
            "event_count": len(events),
            "events": events,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    def load(self, session_id: str) -> dict[str, Any] | None:
        path = self._dir / f"{session_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_sessions(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for p in sorted(self._dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            data = json.loads(p.read_text(encoding="utf-8"))
            results.append(
                {
                    "session_id": data.get("session_id", p.stem),
                    "saved_at": data.get("saved_at", 0),
                    "event_count": data.get("event_count", 0),
                }
            )
        return results

    def delete(self, session_id: str) -> bool:
        return self.delete_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        path = self._dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def cleanup_old(self, max_age_hours: float = 72.0) -> int:
        cutoff = time.time() - max_age_hours * 3600
        count = 0
        for p in self._dir.glob("*.json"):
            if p.stat().st_mtime < cutoff:
                p.unlink()
                count += 1
        return count


_default_store: SessionStore | None = None


def _get_default_store() -> SessionStore:
    global _default_store
    if _default_store is None:
        _default_store = SessionStore()
    return _default_store


def save_session(session: Any) -> Path:
    return _get_default_store().save(session)


def load_session(session_id: str) -> dict[str, Any] | None:
    return _get_default_store().load(session_id)


def list_sessions() -> list[dict[str, Any]]:
    return _get_default_store().list_sessions()


def delete_session(session_id: str) -> bool:
    return _get_default_store().delete_session(session_id)
