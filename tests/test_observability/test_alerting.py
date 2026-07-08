from __future__ import annotations

from unittest.mock import MagicMock

from petfish_bi_cli.observability.alerting import (
    AlertEngine,
    AlertEvent,
    AlertRule,
)
from petfish_bi_cli.observability.metrics import MetricsCollector


class TestAlertRule:
    def test_gt_evaluation(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="gt", severity="warning"
        )
        assert rule.evaluate(11) is True
        assert rule.evaluate(10) is False
        assert rule.evaluate(9) is False

    def test_lt_evaluation(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="lt", severity="warning"
        )
        assert rule.evaluate(9) is True
        assert rule.evaluate(10) is False

    def test_gte_evaluation(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="gte", severity="warning"
        )
        assert rule.evaluate(10) is True
        assert rule.evaluate(9) is False

    def test_lte_evaluation(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="lte", severity="warning"
        )
        assert rule.evaluate(10) is True
        assert rule.evaluate(11) is False

    def test_eq_evaluation(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="eq", severity="info"
        )
        assert rule.evaluate(10) is True
        assert rule.evaluate(10.01) is False

    def test_unknown_comparison_returns_false(self):
        rule = AlertRule(
            name="test", metric_name="x", threshold=10, comparison="weird", severity="info"
        )
        assert rule.evaluate(100) is False


class TestAlertEngine:
    def test_no_rules_no_alerts(self):
        metrics = MetricsCollector()
        engine = AlertEngine(metrics=metrics, rules=[])
        assert engine.check() == []

    def test_metric_below_threshold_no_alert(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 5)
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="high_err",
                    metric_name="errors_total",
                    threshold=10,
                    comparison="gt",
                    severity="critical",
                ),
            ],
        )
        assert engine.check() == []

    def test_metric_above_threshold_fires_alert(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 15)
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="high_err",
                    metric_name="errors_total",
                    threshold=10,
                    comparison="gt",
                    severity="critical",
                ),
            ],
        )
        alerts = engine.check()
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_err"
        assert alerts[0].severity == "critical"
        assert alerts[0].value == 15

    def test_cooldown_prevents_repeat(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 15)
        rule = AlertRule(
            name="high_err",
            metric_name="errors_total",
            threshold=10,
            comparison="gt",
            severity="critical",
            cooldown_seconds=3600,
        )
        engine = AlertEngine(metrics=metrics, rules=[rule])
        first = engine.check()
        assert len(first) == 1
        second = engine.check()
        assert len(second) == 0

    def test_missing_metric_skips_rule(self):
        metrics = MetricsCollector()
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="x",
                    metric_name="nonexistent",
                    threshold=1,
                    comparison="gt",
                    severity="info",
                ),
            ],
        )
        assert engine.check() == []

    def test_custom_handler_called(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 20)
        handler = MagicMock()
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="err",
                    metric_name="errors_total",
                    threshold=10,
                    comparison="gt",
                    severity="critical",
                ),
            ],
            on_alert=handler,
        )
        engine.check()
        handler.assert_called_once()
        event = handler.call_args.args[0]
        assert isinstance(event, AlertEvent)
        assert event.value == 20

    def test_add_rule(self):
        metrics = MetricsCollector()
        engine = AlertEngine(metrics=metrics, rules=[])
        engine.add_rule(
            AlertRule(name="new", metric_name="x", threshold=1, comparison="gt", severity="info")
        )
        assert len(engine._rules) == 1

    def test_multiple_rules_fire_independently(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 20)
        metrics.record("avg_response_time", 45.0)
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="err",
                    metric_name="errors_total",
                    threshold=10,
                    comparison="gt",
                    severity="critical",
                ),
                AlertRule(
                    name="latency",
                    metric_name="avg_response_time",
                    threshold=30,
                    comparison="gt",
                    severity="warning",
                ),
            ],
        )
        alerts = engine.check()
        assert len(alerts) == 2
        names = {a.rule_name for a in alerts}
        assert names == {"err", "latency"}

    def test_default_rules_loaded(self):
        metrics = MetricsCollector()
        engine = AlertEngine(metrics=metrics)
        assert len(engine._rules) == 5

    def test_alert_event_has_timestamp(self):
        metrics = MetricsCollector()
        metrics.record("errors_total", 15)
        engine = AlertEngine(
            metrics=metrics,
            rules=[
                AlertRule(
                    name="err",
                    metric_name="errors_total",
                    threshold=10,
                    comparison="gt",
                    severity="critical",
                ),
            ],
        )
        alerts = engine.check()
        assert alerts[0].timestamp > 0
