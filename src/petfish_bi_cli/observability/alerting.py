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
    comparison: str  # gt | lt | gte | lte | eq
    severity: str    # info | warning | critical
    cooldown_seconds: int = 300
    message_template: str = "{metric_name} = {value} (threshold: {threshold})"

    def evaluate(self, value: float) -> bool:
        if self.comparison == "gt":
            return value > self.threshold
        if self.comparison == "lt":
            return value < self.threshold
        if self.comparison == "gte":
            return value >= self.threshold
        if self.comparison == "lte":
            return value <= self.threshold
        if self.comparison == "eq":
            return abs(value - self.threshold) < 0.01
        return False


@dataclass
class AlertEvent:
    rule_name: str
    severity: str
    value: float
    threshold: float
    message: str
    timestamp: float = field(default_factory=time.time)


class AlertEngine:
    def __init__(
        self,
        metrics: MetricsCollector,
        rules: list[AlertRule] | None = None,
        on_alert: Callable[[AlertEvent], None] | None = None,
    ):
        self._metrics = metrics
        self._rules = rules or _DEFAULT_RULES
        self._on_alert = on_alert or _default_alert_handler
        self._last_fired: dict[str, float] = {}

    def check(self) -> list[AlertEvent]:
        fired: list[AlertEvent] = []
        for rule in self._rules:
            value = self._metrics.get(rule.metric_name)
            if value is None:
                continue
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

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)


_DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        name="high_error_rate",
        metric_name="errors_total",
        threshold=10,
        comparison="gt",
        severity="critical",
        cooldown_seconds=60,
    ),
    AlertRule(
        name="high_latency",
        metric_name="avg_response_time",
        threshold=30.0,
        comparison="gt",
        severity="warning",
        cooldown_seconds=120,
    ),
    AlertRule(
        name="budget_near_limit",
        metric_name="budget_usage_ratio",
        threshold=0.8,
        comparison="gt",
        severity="warning",
        cooldown_seconds=300,
    ),
    AlertRule(
        name="validation_failure_spike",
        metric_name="validation_failures",
        threshold=5,
        comparison="gt",
        severity="critical",
        cooldown_seconds=180,
    ),
    AlertRule(
        name="jobs_stuck",
        metric_name="pending_jobs",
        threshold=20,
        comparison="gt",
        severity="warning",
        cooldown_seconds=600,
    ),
]


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
