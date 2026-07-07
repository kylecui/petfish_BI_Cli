from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class SlaTracker:
    max_samples: int = 1000
    _response_times: deque = field(default_factory=deque)
    _error_count: int = 0
    _total_count: int = 0
    _lock: Lock = field(default_factory=Lock)

    def record(self, response_time: float, success: bool) -> None:
        with self._lock:
            self._response_times.append(response_time)
            if len(self._response_times) > self.max_samples:
                self._response_times.popleft()
            self._total_count += 1
            if not success:
                self._error_count += 1

    def percentile(self, p: float) -> float:
        with self._lock:
            if not self._response_times:
                return 0.0
            sorted_times = sorted(self._response_times)
            idx = int(len(sorted_times) * p / 100)
            idx = min(idx, len(sorted_times) - 1)
            return round(sorted_times[idx], 3)

    @property
    def error_rate(self) -> float:
        with self._lock:
            if self._total_count == 0:
                return 0.0
            return round(self._error_count / self._total_count * 100, 2)

    @property
    def availability(self) -> float:
        with self._lock:
            if self._total_count == 0:
                return 100.0
            return round((1 - self._error_count / self._total_count) * 100, 2)

    @property
    def total_requests(self) -> int:
        with self._lock:
            return self._total_count

    def snapshot(self) -> dict:
        return {
            "p50_response_time_s": self.percentile(50),
            "p95_response_time_s": self.percentile(95),
            "p99_response_time_s": self.percentile(99),
            "error_rate_percent": self.error_rate,
            "availability_percent": self.availability,
            "total_requests": self.total_requests,
        }


_sla_tracker = SlaTracker()


def get_sla_tracker() -> SlaTracker:
    return _sla_tracker
