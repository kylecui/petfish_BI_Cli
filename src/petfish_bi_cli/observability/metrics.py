from __future__ import annotations

import json as _json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("petfish_bi_cli")


@dataclass
class MetricEvent:
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self):
        self._events: list[MetricEvent] = []
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, tags: dict[str, str] | None = None) -> None:
        self._counters[name] += 1
        self._events.append(MetricEvent(name=name, value=1, tags=tags or {}))

    def timing(self, name: str, duration: float, tags: dict[str, str] | None = None) -> None:
        self._timers[name].append(duration)
        self._events.append(MetricEvent(name=name, value=duration, tags=tags or {}))

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._gauges[name] = value
        self._events.append(MetricEvent(name=name, value=value, tags=tags or {}))

    def get_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def get_events(self) -> list[MetricEvent]:
        return list(self._events)

    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._events.append(MetricEvent(name=name, value=value, tags=tags or {}))
        self._gauges[name] = value

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_timer_stats(self, name: str) -> dict[str, float]:
        values = self._timers.get(name, [])
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": float(n),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(sorted_vals) / n,
            "p50": sorted_vals[n // 2],
            "p99": sorted_vals[min(int(n * 0.99), n - 1)],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "counters": self.get_counters(),
            "timers": {k: self.get_timer_stats(k) for k in self._timers},
            "gauges": dict(self._gauges),
            "total_events": len(self._events),
        }


_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def reset_metrics() -> None:
    global _metrics
    _metrics = MetricsCollector()


class StructuredLogger:
    """JSONL structured logging with trace correlation."""

    def __init__(self, name: str = "petfish_bi_cli"):
        self._logger = logging.getLogger(name)
        self._trace: dict[str, str] = {}

    def set_trace(self, session_id: str, query_id: str | None = None) -> None:
        self._trace = {"session_id": session_id}
        if query_id:
            self._trace["query_id"] = query_id

    def clear_trace(self) -> None:
        self._trace = {}

    def log(self, level: str, event: str, **fields: Any) -> None:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "level": level,
            "event": event,
            **self._trace,
            **fields,
        }
        line = _json.dumps(entry, ensure_ascii=False, default=str)
        getattr(self._logger, level.lower(), self._logger.info)(line)

    def info(self, event: str, **fields: Any) -> None:
        self.log("info", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log("warning", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log("error", event, **fields)

    def debug(self, event: str, **fields: Any) -> None:
        self.log("debug", event, **fields)


_structured: StructuredLogger | None = None


def get_structured_logger() -> StructuredLogger:
    global _structured
    if _structured is None:
        _structured = StructuredLogger()
    return _structured


@dataclass
class AlertRule:
    name: str
    metric: str
    threshold: float
    comparison: str  # gt | lt | gte | lte
    description: str = ""
    severity: str = "warning"  # warning | critical

    def check(self, metrics: MetricsCollector) -> AlertResult:
        actual = self._extract_value(metrics)
        triggered = self._compare(actual)
        return AlertResult(
            rule_name=self.name,
            triggered=triggered,
            actual_value=actual,
            threshold=self.threshold,
            severity=self.severity if triggered else "ok",
            message=f"{self.metric}={actual:.4f} {self.comparison} {self.threshold}"
            if triggered
            else "",
        )

    def _extract_value(self, metrics: MetricsCollector) -> float:
        if self.metric == "error_rate":
            total = metrics.get_counters().get("queries.total", 0)
            errors = sum(v for k, v in metrics.get_counters().items() if k.startswith("error."))
            return errors / total if total > 0 else 0.0

        if self.metric == "p99_latency":
            stats = metrics.get_timer_stats("query.duration_seconds")
            return stats.get("p99", 0.0)

        if self.metric == "budget_exceeded_rate":
            total = metrics.get_counters().get("queries.total", 0)
            exceeded = metrics.get_counters().get("error.budget_exceeded", 0)
            return exceeded / total if total > 0 else 0.0

        if self.metric == "validation_failure_rate":
            total = metrics.get_counters().get("validation.passed", 0) + metrics.get_counters().get(
                "validation.failed", 0
            )
            failed = metrics.get_counters().get("validation.failed", 0)
            return failed / total if total > 0 else 0.0

        return metrics.get_counters().get(self.metric, 0)

    def _compare(self, actual: float) -> bool:
        ops = {
            "gt": lambda a, b: a > b,
            "lt": lambda a, b: a < b,
            "gte": lambda a, b: a >= b,
            "lte": lambda a, b: a <= b,
        }
        return ops.get(self.comparison, lambda a, b: False)(actual, self.threshold)


@dataclass
class AlertResult:
    rule_name: str
    triggered: bool
    actual_value: float
    threshold: float
    severity: str
    message: str


DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule("high_error_rate", "error_rate", 0.10, "gt", "critical"),
    AlertRule("slow_p99", "p99_latency", 30.0, "gt", "warning"),
    AlertRule("budget_burn", "budget_exceeded_rate", 0.05, "gt", "critical"),
    AlertRule("validation_degradation", "validation_failure_rate", 0.20, "gt", "warning"),
]


class AlertEngine:
    def __init__(self, rules: list[AlertRule] | None = None):
        self._rules = rules or list(DEFAULT_ALERT_RULES)
        self._history: list[AlertResult] = []

    def evaluate(self, metrics: MetricsCollector) -> list[AlertResult]:
        results = [rule.check(metrics) for rule in self._rules]
        triggered = [r for r in results if r.triggered]
        self._history.extend(triggered)
        return results

    def get_triggered(self) -> list[AlertResult]:
        return [r for r in self._history if r.triggered]

    def get_history(self) -> list[AlertResult]:
        return list(self._history)


_alert_engine: AlertEngine | None = None


def get_alert_engine() -> AlertEngine:
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine()
    return _alert_engine


class LoggingMiddleware:
    def __init__(self, metrics: MetricsCollector | None = None):
        self._metrics = metrics or get_metrics()
        self._slog = get_structured_logger()

    def on_query_start(self, query: str) -> float:
        start = time.time()
        self._metrics.increment("queries.total")
        self._slog.info("query_start", query=query[:100])
        return start

    def on_query_end(self, query: str, start: float, status: str, session_id: str) -> None:
        duration = time.time() - start
        self._metrics.timing("query.duration_seconds", duration, {"status": status})
        self._slog.set_trace(session_id=session_id)
        self._slog.info("query_end", status=status, duration_s=round(duration, 2))
        self._slog.clear_trace()

    def on_tool_call(self, tool_name: str, success: bool) -> None:
        tag = "success" if success else "failure"
        self._metrics.increment(f"tool.{tool_name}", {"result": tag})
        self._slog.debug("tool_call", tool=tool_name, result=tag)

    def on_validation(self, passed: bool, errors: list[str]) -> None:
        if passed:
            self._metrics.increment("validation.passed")
        else:
            self._metrics.increment("validation.failed")
            for err in errors:
                self._slog.warning("validation_error", error=err)

    def on_error(self, error_type: str, message: str) -> None:
        self._metrics.increment(f"error.{error_type}")
        self._slog.error("error", type=error_type, message=message)
