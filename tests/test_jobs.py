from __future__ import annotations

from petfish_bi_cli.domain import BIQuery
from petfish_bi_cli.jobs import JobRegistry


class TestJobRegistry:
    def test_create_returns_job_id(self):
        reg = JobRegistry()
        job_id = reg.create(BIQuery(prompt="test"))
        assert len(job_id) > 0

    def test_get_returns_job(self):
        reg = JobRegistry()
        job_id = reg.create(BIQuery(prompt="test"))
        job = reg.get(job_id)
        assert job is not None
        assert job.status == "pending"
        assert job.query.prompt == "test"

    def test_get_unknown_returns_none(self):
        reg = JobRegistry()
        assert reg.get("nonexistent") is None

    def test_update_to_completed(self):
        reg = JobRegistry()
        job_id = reg.create(BIQuery(prompt="test"))
        reg.update(job_id, status="running")
        assert reg.get(job_id).status == "running"
        reg.update(job_id, status="completed")
        assert reg.get(job_id).status == "completed"
        assert reg.get(job_id).completed_at is not None

    def test_update_unknown_job_no_error(self):
        reg = JobRegistry()
        reg.update("nonexistent", status="completed")

    def test_concurrent_create(self):
        import threading

        reg = JobRegistry()
        ids = []

        def create_one():
            jid = reg.create(BIQuery(prompt="test"))
            ids.append(jid)

        threads = [threading.Thread(target=create_one) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(ids) == 10
        assert len(set(ids)) == 10
