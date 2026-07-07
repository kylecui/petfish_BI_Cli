from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.domain import BIQuery, BIReport


@dataclass
class JobStatus:
    job_id: str
    status: str  # pending | running | completed | failed
    query: BIQuery
    result: BIReport | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class JobRegistry:
    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}
        self._lock = threading.Lock()

    def create(self, query: BIQuery) -> str:
        job_id = uuid.uuid4().hex[:16]
        with self._lock:
            self._jobs[job_id] = JobStatus(job_id=job_id, status="pending", query=query)
        return job_id

    def get(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, status: str,
               result: BIReport | None = None, error: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.result = result
                job.error = error
                if status in ("completed", "failed"):
                    job.completed_at = time.time()


_registry = JobRegistry()


def get_registry() -> JobRegistry:
    return _registry


async def run_job_async(job_id: str, query: BIQuery, app: BIApplication) -> None:
    _registry.update(job_id, status="running")
    try:
        report = await asyncio.to_thread(app.execute, query)
        _registry.update(job_id, status="completed", result=report)
    except Exception as exc:
        _registry.update(job_id, status="failed", error=str(exc))
