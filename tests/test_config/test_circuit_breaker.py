"""Tests for CircuitBreaker model adapter wrapper."""
from __future__ import annotations

import pytest
from petfishframework.core.types import Message, ModelRequest, ModelResponse, Role, Usage
from petfishframework.reliability.circuit_breaker import CircuitBreaker, CircuitState

from petfish_bi_cli.config.circuit_breaker import CircuitBreakerModelAdapter


class FakeInnerModel:
    name = "fake-inner"

    def __init__(self, fail_times: int = 0):
        self._fail_remaining = fail_times
        self.query_count = 0

    def query(self, request):
        self.query_count += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise RuntimeError("API error")
        return ModelResponse(
            content="ok",
            tool_calls=(),
            usage=Usage(),
            finish_reason="stop",
        )


class TestCircuitBreakerModelAdapter:
    def test_passes_through_on_success(self):
        inner = FakeInnerModel()
        breaker = CircuitBreaker(failure_threshold=3)
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        req = ModelRequest(messages=(Message(role=Role.USER, content="hi"),))
        result = adapter.query(req)
        assert result.content == "ok"
        assert breaker.state is CircuitState.CLOSED

    def test_records_failure_on_exception(self):
        inner = FakeInnerModel(fail_times=2)
        breaker = CircuitBreaker(failure_threshold=3)
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        req = ModelRequest(messages=(Message(role=Role.USER, content="hi"),))
        with pytest.raises(RuntimeError):
            adapter.query(req)
        assert breaker.state is CircuitState.CLOSED
        with pytest.raises(RuntimeError):
            adapter.query(req)
        assert breaker.state is CircuitState.CLOSED
        assert inner.query_count == 2

    def test_opens_circuit_after_threshold(self):
        inner = FakeInnerModel(fail_times=10)
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_s=60)
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        req = ModelRequest(messages=(Message(role=Role.USER, content="hi"),))
        for _ in range(3):
            with pytest.raises(RuntimeError):
                adapter.query(req)
        assert breaker.state is CircuitState.OPEN

    def test_blocks_call_when_open(self):
        inner = FakeInnerModel(fail_times=10)
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_s=60)
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        req = ModelRequest(messages=(Message(role=Role.USER, content="hi"),))
        for _ in range(2):
            with pytest.raises(RuntimeError):
                adapter.query(req)
        assert breaker.state is CircuitState.OPEN
        with pytest.raises(RuntimeError, match="[Cc]ircuit"):
            adapter.query(req)
        assert inner.query_count == 2

    def test_name_proxies_inner(self):
        inner = FakeInnerModel()
        breaker = CircuitBreaker()
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        assert adapter.name == "fake-inner"

    def test_recovers_after_success(self):
        inner = FakeInnerModel(fail_times=1)
        breaker = CircuitBreaker(failure_threshold=5)
        adapter = CircuitBreakerModelAdapter(inner, breaker)
        req = ModelRequest(messages=(Message(role=Role.USER, content="hi"),))
        with pytest.raises(RuntimeError):
            adapter.query(req)
        result = adapter.query(req)
        assert result.content == "ok"
        assert breaker.state is CircuitState.CLOSED
