from __future__ import annotations

from petfish_bi_cli.persistence import list_sessions, load_session, save_session


class TestSessionPersistence:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", tmp_path)
        events = [
            {"type": "model_call", "input": "test", "output": "result"},
            {"type": "tool_call", "tool": "load_data", "result": {"claims": []}},
        ]
        path = save_session("ses_test_001", events)
        assert path.exists()
        loaded = load_session("ses_test_001")
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["type"] == "model_call"

    def test_load_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", tmp_path)
        result = load_session("nonexistent")
        assert result is None

    def test_list_sessions(self, tmp_path, monkeypatch):
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", tmp_path)
        save_session("ses_a", [{"type": "test"}])
        save_session("ses_b", [{"type": "test"}])
        sessions = list_sessions()
        assert "ses_a" in sessions
        assert "ses_b" in sessions
        assert len(sessions) == 2

    def test_list_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", tmp_path)
        assert list_sessions() == []

    def test_unicode_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", tmp_path)
        events = [{"query": "CROCS在京东的价格", "answer": "424.0元"}]
        save_session("ses_unicode", events)
        loaded = load_session("ses_unicode")
        assert loaded is not None
        assert "CROCS" in loaded[0]["query"]

    def test_creates_directory(self, tmp_path, monkeypatch):
        target = tmp_path / "nested" / "sessions"
        monkeypatch.setattr("petfish_bi_cli.persistence.SESSIONS_DIR", target)
        save_session("ses_mkdir", [{"type": "test"}])
        assert target.exists()
