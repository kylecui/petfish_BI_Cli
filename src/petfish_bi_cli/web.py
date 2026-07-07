from __future__ import annotations

import asyncio

from pydantic import BaseModel

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.domain import BIQuery
from petfish_bi_cli.jobs import get_registry, run_job_async


class AnalyzeRequest(BaseModel):
    query: str
    data_sources: list[str] = []


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


def create_app():
    from fastapi import FastAPI

    app = FastAPI(title="petfish BI CLI API", version="0.1.0")
    registry = get_registry()

    @app.post("/analyze", response_model=AnalyzeResponse, status_code=202)
    async def analyze(req: AnalyzeRequest):
        bi_query = BIQuery(prompt=req.query, data_sources=tuple(req.data_sources))
        job_id = registry.create(bi_query)
        bi_app = BIApplication()
        asyncio.create_task(run_job_async(job_id, bi_query, bi_app))
        return AnalyzeResponse(job_id=job_id, status="pending")

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        job = registry.get(job_id)
        if job is None:
            return {"error": "Job not found", "job_id": job_id}
        result: dict = {"job_id": job.job_id, "status": job.status}
        if job.result:
            result["answer"] = job.result.answer
            result["data"] = job.result.data
            result["report_status"] = job.result.status
        if job.error:
            result["error"] = job.error
        return result

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
