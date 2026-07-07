from __future__ import annotations

import asyncio
import time

from pydantic import BaseModel

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.domain import BIQuery
from petfish_bi_cli.jobs import get_registry, run_job_async
from petfish_bi_cli.observability.audit import get_audit_logger
from petfish_bi_cli.observability.sla import get_sla_tracker


class AnalyzeRequest(BaseModel):
    query: str
    data_sources: list[str] = []


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


def create_app():
    from fastapi import FastAPI, Header, HTTPException, Request

    from petfish_bi_cli.compliance.checker import (
        load_sla_config,
        redact_pii,
        verify_api_key,
    )
    from petfish_bi_cli.observability.metrics import get_metrics
    from petfish_bi_cli.web.rate_limit import RateLimiter

    app = FastAPI(title="petfish BI CLI API", version="0.1.0")
    registry = get_registry()
    sla_config = load_sla_config()
    rate_limiter = RateLimiter(sla_config)
    audit = get_audit_logger()
    sla = get_sla_tracker()
    metrics = get_metrics()

    @app.post("/analyze", response_model=AnalyzeResponse, status_code=202)
    async def analyze(
        req: AnalyzeRequest,
        request: Request,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ):
        key = verify_api_key(x_api_key, sla_config)
        allowed, reason = rate_limiter.check(key)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)

        start = time.time()
        redacted = redact_pii(req.query)
        bi_query = BIQuery(prompt=req.query, data_sources=tuple(req.data_sources))
        job_id = registry.create(bi_query)
        bi_app = BIApplication()
        asyncio.create_task(run_job_async(job_id, bi_query, bi_app))

        elapsed = time.time() - start
        sla.record(elapsed, success=True)
        metrics.record_query("analyze", elapsed)
        audit.log(key, redacted, "pending", elapsed, session_id=job_id)
        return AnalyzeResponse(job_id=job_id, status="pending")

    @app.get("/jobs/{job_id}")
    async def get_job(
        job_id: str,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ):
        key = verify_api_key(x_api_key, sla_config)
        allowed, reason = rate_limiter.check(key)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)

        start = time.time()
        job = registry.get(job_id)
        if job is None:
            elapsed = time.time() - start
            sla.record(elapsed, success=False)
            audit.log(key, f"job:{job_id}", "not_found", elapsed)
            raise HTTPException(status_code=404, detail="Job not found")

        result: dict = {"job_id": job.job_id, "status": job.status}
        if job.result:
            result["answer"] = job.result.answer
            result["data"] = job.result.data
            result["report_status"] = job.result.status
        if job.error:
            result["error"] = job.error

        elapsed = time.time() - start
        sla.record(elapsed, success=True)
        audit.log(key, f"job:{job_id}", job.status, elapsed, session_id=job_id)
        return result

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/metrics")
    async def prometheus_metrics():
        return metrics.to_prometheus()

    @app.get("/sla")
    async def sla_status(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ):
        key = verify_api_key(x_api_key, sla_config)
        return sla.snapshot()

    @app.get("/rate-limit")
    async def rate_limit_status(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ):
        key = verify_api_key(x_api_key, sla_config)
        return rate_limiter.remaining(key)

    return app
