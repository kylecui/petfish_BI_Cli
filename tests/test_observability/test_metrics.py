from __future__ import annotations

from petfish_bi_cli.observability.metrics import (
    LoggingMiddleware,
    MetricsCollector,
    get_metrics,
    reset_metrics,
)


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("queries.total")
        m.increment("queries.total")
        assert m.get_counters()["queries.total"] == 2

    def test_timing_stats(self):
        m = MetricsCollector()
        m.timing("duration", 1.0)
        m.timing("duration", 2.0)
        m.timing("duration", 3.0)
        stats = m.get_timer_stats("duration")
        assert stats["count"] == 3
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["avg"] == 2.0

    def test_gauge(self):
        m = MetricsCollector()
        m.gauge("memory_mb", 512.0)
        assert len(m._events) == 1

    def test_summary(self):
        m = MetricsCollector()
        m.increment("test.counter")
        m.timing("test.timer", 0.5)
        s = m.summary()
        assert "counters" in s
        assert "timers" in s
        assert s["total_events"] == 2

    def test_empty_timer_stats(self):
        m = MetricsCollector()
        assert m.get_timer_stats("nonexistent") == {}


class TestLoggingMiddleware:
    def test_on_query_start_returns_timestamp(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        start = m.on_query_start("test query")
        assert isinstance(start, float)
        assert m._metrics.get_counters()["queries.total"] == 1

    def test_on_query_end_records_duration(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        start = m.on_query_start("test")
        m.on_query_end("test", start, "ok", "ses_123")
        stats = m._metrics.get_timer_stats("query.duration_seconds")
        assert stats["count"] == 1

    def test_on_tool_call_success(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        m.on_tool_call("load_data", True)
        assert m._metrics.get_counters()["tool.load_data"] == 1

    def test_on_tool_call_failure(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        m.on_tool_call("load_data", False)
        assert m._metrics.get_counters()["tool.load_data"] == 1

    def test_on_validation_passed(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        m.on_validation(True, [])
        assert m._metrics.get_counters()["validation.passed"] == 1
        assert m._metrics.get_counters().get("validation.failed", 0) == 0

    def test_on_validation_failed(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        m.on_validation(False, ["number mismatch"])
        assert m._metrics.get_counters()["validation.failed"] == 1

    def test_on_error(self):
        m = LoggingMiddleware(metrics=MetricsCollector())
        m.on_error("timeout", "request timed out")
        assert m._metrics.get_counters()["error.timeout"] == 1


class TestGlobalMetrics:
    def test_get_metrics_singleton(self):
        reset_metrics()
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_reset_metrics(self):
        m = get_metrics()
        m.increment("test")
        reset_metrics()
        m2 = get_metrics()
        assert m2.get_counters() == {}
