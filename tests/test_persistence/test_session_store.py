from __future__ import annotations

import time

from petfish_bi_cli.persistence.session_store import SessionStore


class TestSessionStore:
    def test_save_and_load(self, tmp_path):
        store = SessionStore(base_dir=tmp_path)
        session_id = f"test_{int(time.time())}"
        mock_session = type("MockSession", (), {"session_id": session_id})()
        mock_session._emitter = None

        path = store.save(mock_session)
        assert path.exists()

        loaded = store.load(session_id)
        assert loaded is not None
        assert loaded["session_id"] == session_id

    def test_load_nonexistent_returns_none(self, tmp_path):
        store = SessionStore(base_dir=tmp_path)
        assert store.load("nonexistent") is None

    def test_list_sessions(self, tmp_path):
        store = SessionStore(base_dir=tmp_path)
        for i in range(3):
            sid = f"session_{i}"
            mock = type("MockSession", (), {"session_id": sid, "_emitter": None})()
            store.save(mock)

        sessions = store.list_sessions()
        assert len(sessions) == 3
        assert all("session_id" in s for s in sessions)

    def test_delete(self, tmp_path):
        store = SessionStore(base_dir=tmp_path)
        sid = "deletable"
        mock = type("MockSession", (), {"session_id": sid, "_emitter": None})()
        store.save(mock)
        assert store.delete(sid) is True
        assert store.load(sid) is None
        assert store.delete(sid) is False

    def test_cleanup_old(self, tmp_path):
        store = SessionStore(base_dir=tmp_path)
        old_file = tmp_path / "old.json"
        old_file.write_text('{"session_id": "old", "saved_at": 0, "event_count": 0}')
        import os
        old_time = time.time() - 100 * 3600
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "new.json"
        new_file.write_text('{"session_id": "new", "saved_at": 0, "event_count": 0}')

        deleted = store.cleanup_old(max_age_hours=72)
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_save_creates_directory(self, tmp_path):
        new_dir = tmp_path / "nested" / "sessions"
        store = SessionStore(base_dir=new_dir)
        assert new_dir.exists()
