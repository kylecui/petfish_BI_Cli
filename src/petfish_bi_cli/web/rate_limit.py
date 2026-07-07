from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

from petfish_bi_cli.compliance.checker import SlaConfig


@dataclass
class RateLimitEntry:
    minute_requests: deque = field(default_factory=deque)
    day_requests: deque = field(default_factory=deque)


class RateLimiter:
    def __init__(self, config: SlaConfig):
        self._config = config
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = Lock()

    def check(self, api_key: str) -> tuple[bool, str | None]:
        now = time.time()
        with self._lock:
            entry = self._entries[api_key]
            self._purge_old(entry, now)

            if len(entry.minute_requests) >= self._config.rate_limit_per_minute:
                return False, f"Rate limit exceeded: {self._config.rate_limit_per_minute}/min"

            if len(entry.day_requests) >= self._config.rate_limit_per_day:
                return False, f"Rate limit exceeded: {self._config.rate_limit_per_day}/day"

            entry.minute_requests.append(now)
            entry.day_requests.append(now)
            return True, None

    def remaining(self, api_key: str) -> dict[str, int]:
        now = time.time()
        with self._lock:
            entry = self._entries[api_key]
            self._purge_old(entry, now)
            return {
                "minute": max(0, self._config.rate_limit_per_minute - len(entry.minute_requests)),
                "day": max(0, self._config.rate_limit_per_day - len(entry.day_requests)),
            }

    @staticmethod
    def _purge_old(entry: RateLimitEntry, now: float) -> None:
        minute_ago = now - 60
        day_ago = now - 86400
        while entry.minute_requests and entry.minute_requests[0] < minute_ago:
            entry.minute_requests.popleft()
        while entry.day_requests and entry.day_requests[0] < day_ago:
            entry.day_requests.popleft()
