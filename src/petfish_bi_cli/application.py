from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

from petfishframework.core.structured import StructuredResult, parse_structured
from petfishframework.core.types import Budget, BudgetExceeded, Task

from petfish_bi_cli.domain import BIQuery, BIReport
from petfish_bi_cli.framework import make_bi_agent
from petfish_bi_cli.grounding.claims import ClaimsRegistry
from petfish_bi_cli.grounding.validator import validate_report
from petfish_bi_cli.observability.siem import PIIRedactingSink, make_siem_sink


@dataclass
class _SessionRecord:
    session_id: str
    query: BIQuery
    registry: ClaimsRegistry


class BIApplication:
    def __init__(
        self,
        data_root: Path | None = None,
        semantic_dir: Path | None = None,
    ):
        self._data_root = data_root or Path("references")
        self._semantic_dir = semantic_dir or self._data_root / "semantic"
        self._sessions: dict[str, _SessionRecord] = {}

    def execute(
        self,
        query: BIQuery,
        budget: Budget | None = None,
        model=None,
    ) -> BIReport:
        registry = ClaimsRegistry()
        agent = make_bi_agent(
            model=model,
            data_root=self._data_root,
            semantic_dir=self._semantic_dir,
            registry=registry,
        )

        field_names = [f.name for f in fields(BIReport)]
        augmented_prompt = (
            f"{query.prompt}\n\nReturn your answer as JSON with these fields: {field_names}"
        )
        task = Task(prompt=augmented_prompt, metadata=dict(query.metadata))

        try:
            result = self._run_with_siem(agent, task, budget)
        except BudgetExceeded as exc:
            return BIReport(
                answer=f"Budget exceeded: {exc}",
                status="budget_exceeded",
            )

        if result.data is None:
            return BIReport(
                answer=result.answer,
                status="parse_error",
                session_id=result.session_id,
            )

        report = result.data
        if registry.count > 0:
            validation = validate_report(
                report_answer=report.answer,
                report_data=report.data,
                claims=registry.to_ledger(),
            )
            if not validation.valid:
                return BIReport(
                    answer=report.answer,
                    data=report.data,
                    session_id=result.session_id,
                    status="validation_failed",
                )

        if not report.session_id:
            report = BIReport(
                answer=report.answer,
                data=report.data,
                session_id=result.session_id,
                usage=report.usage,
                rich_content=report.rich_content,
                status=report.status,
            )

        self._sessions[result.session_id] = _SessionRecord(
            session_id=result.session_id,
            query=query,
            registry=registry,
        )

        return report

    @staticmethod
    def _run_with_siem(agent, task: Task, budget: Budget | None) -> StructuredResult:
        """Create a Session, wire audit sinks, run, and parse structured output."""
        session = agent.session(task, budget=budget)

        siem = make_siem_sink()
        session.events.subscribe(PIIRedactingSink(siem))

        _try_subscribe_otel(session.events)

        run_result = session.run()
        try:
            parsed = parse_structured(run_result.answer, BIReport)
            return StructuredResult(
                answer=run_result.answer,
                data=parsed,
                parse_error=None,
                session_id=run_result.session_id,
            )
        except ValueError as exc:
            return StructuredResult(
                answer=run_result.answer,
                data=None,
                parse_error=str(exc),
                session_id=run_result.session_id,
            )

    def get_session(self, session_id: str) -> _SessionRecord | None:
        return self._sessions.get(session_id)


def _try_subscribe_otel(events) -> None:
    """Subscribe OTelSink if opentelemetry is available; degrade to no-op."""
    try:
        from petfishframework.observability import OTelSink

        events.subscribe(OTelSink())
    except Exception:
        pass
