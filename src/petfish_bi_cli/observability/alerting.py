from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from petfish_bi_cli.observability.metrics import MetricsCollector


@dataclass(frozen=True)
class AlertRule:
    name: str
    metric_name: str
    threshold: float
    comparison: str
    severity: str
    cooldown_seconds: int = 300
    message_template: str = "{metric_name} = {value} (threshold: {threshold})"

    def evaluate(self, value: float) -> bool:
        ops = {
            "gt": lambda a, b: a > b,
            "lt": lambda a, b: a < b,
            "gte": lambda a, b: a >= b,
            "lte": lambda a, b: a <= b,
            "eq": lambda a, b: abs(a - b) < 1e-9,
        }
        return ops.get(self.comparison, lambda a, b: False)(value, self.threshold)

    def check(self, metrics: MetricsCollector) -> AlertResult:
        value = self._extract_value(metrics)
        triggered = self.evaluate(value)
        return AlertResult(
            rule_name=self.name,
            triggered=triggered,
            actual_value=value,
            threshold=self.threshold,
            severity=self.severity if triggered else "ok",
            message=self.message_template.format(
                metric_name=self.metric_name,
                value=value,
                threshold=self.threshold,
            )
            if triggered
            else "",
        )

    def _extract_value(self, metrics: MetricsCollector) -> float:
        counters = metrics.get_counters()
        gauges = metrics.get_gauges()
        if self.metric_name == "error_rate":
            total = counters.get("queries.total", 0)
            errors = sum(v for k, v in counters.items() if k.startswith("error."))
            return errors / total if total > 0 else 0.0
        if self.metric_name == "p99_latency":
            stats = metrics.get_timer_stats("query.duration_seconds")
            return stats.get("p99", 0.0)
        if self.metric_name == "budget_exceeded_rate":
            total = counters.get("queries.total", 0)
            exceeded = counters.get("error.budget_exceeded", 0)
            return exceeded / total if total > 0 else 0.0
        if self.metric_name == "validation_failure_rate":
            total = counters.get("validation.passed", 0) + counters.get("validation.failed", 0)
            failed = counters.get("validation.failed", 0)
            return failed / total if total > 0 else 0.0
        if self.metric_name in gauges:
            return float(gauges[self.metric_name])
        return float(counters.get(self.metric_name, 0))


@dataclass
class AlertEvent:
    rule_name: str
    severity: str
    value: float
    threshold: float
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AlertResult:
    rule_name: str
    triggered: bool
    actual_value: float
    threshold: float
    severity: str
    message: str


DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule("high_error_rate", "error_rate", 0.10, "gt", "critical", 60),
    AlertRule("slow_p99", "p99_latency", 30.0, "gt", "warning", 120),
    AlertRule("budget_burn", "budget_exceeded_rate", 0.05, "gt", "critical", 300),
    AlertRule("validation_degradation", "validation_failure_rate", 0.20, "gt", "warning", 180),
    AlertRule("jobs_stuck", "pending_jobs", 20, "gt", "warning", 600),
]


class AlertEngine:
    def __init__(
        self,
        metrics: MetricsCollector | None = None,
        rules: list[AlertRule] | None = None,
        on_alert: Callable[[AlertEvent], None] | None = None,
    ):
        self._metrics = metrics or MetricsCollector()
        self._rules = list(rules) if rules is not None else list(DEFAULT_ALERT_RULES)
        self._on_alert = on_alert or _default_alert_handler
        self._last_fired: dict[str, float] = {}
        self._history: list[AlertResult] = []

    def check(self) -> list[AlertEvent]:
        fired: list[AlertEvent] = []
        for rule in self._rules:
            value = rule._extract_value(self._metrics)
            if not rule.evaluate(value):
                continue
            last = self._last_fired.get(rule.name, 0)
            if time.time() - last < rule.cooldown_seconds:
                continue
            event = AlertEvent(
                rule_name=rule.name,
                severity=rule.severity,
                value=value,
                threshold=rule.threshold,
                message=rule.message_template.format(
                    metric_name=rule.metric_name,
                    value=value,
                    threshold=rule.threshold,
                ),
            )
            self._last_fired[rule.name] = time.time()
            self._on_alert(event)
            fired.append(event)
        return fired

    def evaluate(self) -> list[AlertResult]:
        results = [rule.check(self._metrics) for rule in self._rules]
        triggered = [r for r in results if r.triggered]
        self._history.extend(triggered)
        return results

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def get_triggered(self) -> list[AlertResult]:
        return [r for r in self._history if r.triggered]

    def get_history(self) -> list[AlertResult]:
        return list(self._history)


def _default_alert_handler(event: AlertEvent) -> None:
    import json
    import sys

    log_entry = {
        "timestamp": event.timestamp,
        "level": event.severity.upper(),
        "alert": event.rule_name,
        "value": event.value,
        "threshold": event.threshold,
        "message": event.message,
    }
    print(json.dumps(log_entry, ensure_ascii=False), file=sys.stderr)
