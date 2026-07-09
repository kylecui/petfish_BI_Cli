"""CircuitBreaker model adapter wrapper — protects against model API failures."""
from __future__ import annotations

from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import ModelRequest, ModelResponse
from petfishframework.reliability.circuit_breaker import CircuitBreaker


class CircuitBreakerModelAdapter(ModelAdapter):
    """Wraps a ModelAdapter with circuit breaker protection."""

    def __init__(self, inner: ModelAdapter, breaker: CircuitBreaker):
        self._inner = inner
        self._breaker = breaker

    @property
    def name(self) -> str:
        return self._inner.name

    def query(self, request: ModelRequest) -> ModelResponse:
        if not self._breaker.allow():
            raise RuntimeError(
                "Circuit breaker is OPEN — model API appears unavailable. "
                f"State: {self._breaker.state.value}"
            )
        try:
            result = self._inner.query(request)
            self._breaker.record_success()
            return result
        except Exception:
            self._breaker.record_failure()
            raise
