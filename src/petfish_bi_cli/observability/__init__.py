from __future__ import annotations

from petfish_bi_cli.observability.metrics import MetricEvent, MetricsCollector, get_metrics

__all__ = ["MetricsCollector", "MetricEvent", "get_metrics", "StructuredLogger", "get_logger"]


class StructuredLogger:
    def __init__(self, name: str = "bi_cli"):
        self._name = name

    def info(self, msg: str, **kwargs):
        import json
        import time
        entry = {"ts": time.time(), "level": "info", "logger": self._name, "msg": msg, **kwargs}
        print(json.dumps(entry, ensure_ascii=False))

    def error(self, msg: str, **kwargs):
        import json
        import time
        entry = {"ts": time.time(), "level": "error", "logger": self._name, "msg": msg, **kwargs}
        print(json.dumps(entry, ensure_ascii=False))


def get_logger(name: str = "bi_cli") -> StructuredLogger:
    return StructuredLogger(name)
