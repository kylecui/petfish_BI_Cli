from __future__ import annotations

import pytest

from petfish_bi_cli.web import create_app


@pytest.fixture
def client():
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi not installed")
    app = create_app()
    return TestClient(app)


class TestWebAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_post_analyze_returns_202(self, client):
        resp = client.post("/analyze", json={"query": "test query", "data_sources": []})
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    def test_get_job_unknown(self, client):
        resp = client.get("/jobs/nonexistent")
        data = resp.json()
        assert "error" in data or data.get("status") == "not_found"

    def test_openapi_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema.get("paths", {})
        assert "/analyze" in paths
        assert "/jobs/{job_id}" in paths
        assert "/health" in paths
