from __future__ import annotations

import json
import logging

from petfish_bi_cli.observability import (
    MetricsCollector,
    StructuredLogger,
    get_logger,
    get_metrics,
)


class TestStructuredLogger:
    def test_logger_singleton(self):
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_log_info(self, caplog):
        logger = StructuredLogger("test_logger_1")
        with caplog.at_level(logging.INFO, logger="test_logger_1"):
            logger.info("test_event", session_id="ses_123", latency_ms=42)
        assert any("test_event" in r.message for r in caplog.records)

    def test_json_output(self, capsys):
        logger = StructuredLogger("test_logger_2")
        logger.info("json_event", session_id="ses_456")
        captured = capsys.readouterr()
        parsed = json.loads(captured.err.strip() if captured.err else captured.out.strip())
        assert parsed["event"] == "json_event"
        assert parsed["session_id"] == "ses_456"

    def test_log_levels(self, caplog):
        logger = StructuredLogger("test_logger_3")
        with caplog.at_level(logging.DEBUG, logger="test_logger_3"):
            logger.debug("debug_event")
            logger.warning("warn_event")
            logger.error("error_event")
        messages = [r.message for r in caplog.records]
        assert "debug_event" in messages
        assert "warn_event" in messages
        assert "error_event" in messages


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("model_calls")
        m.increment("model_calls")
        m.increment("tool_calls")
        snap = m.snapshot()
        assert snap["counter.model_calls"] == 2
        assert snap["counter.tool_calls"] == 1

    def test_record_time(self):
        m = MetricsCollector()
        m.record_time("query_latency", 1.5)
        m.record_time("query_latency", 2.5)
        snap = m.snapshot()
        assert snap["timer.query_latency_count"] == 2
        assert snap["timer.query_latency_avg_s"] == 2.0

    def test_record_value(self):
        m = MetricsCollector()
        m.record_value("tokens", 100)
        m.record_value("tokens", 200)
        snap = m.snapshot()
        assert snap["value.tokens_sum"] == 300.0
        assert snap["value.tokens_avg"] == 150.0

    def test_save_to_file(self, tmp_path):
        m = MetricsCollector()
        m.increment("test_counter")
        path = m.save(tmp_path / "metrics.json")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["counter.test_counter"] == 1

    def test_metrics_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_empty_snapshot(self):
        m = MetricsCollector()
        snap = m.snapshot()
        assert snap == {}
