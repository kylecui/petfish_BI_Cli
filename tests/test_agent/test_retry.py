from __future__ import annotations

from petfish_bi_cli.agent.retry import safe_execute, with_retry


class TestWithRetry:
    def test_succeeds_first_try(self):
        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0)
        def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert func() == "ok"
        assert call_count == 1

    def test_succeeds_after_retry(self):
        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")
            return "ok"

        assert func() == "ok"
        assert call_count == 2

    def test_exhausts_retries(self):
        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent")

        try:
            func()
            raise AssertionError("should have raised")
        except ValueError:
            pass
        assert call_count == 3

    def test_specific_exception_only(self):
        call_count = 0

        @with_retry(max_attempts=3, delay_seconds=0, exceptions=(ConnectionError,))
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retried")

        try:
            func()
            raise AssertionError("should have raised")
        except ValueError:
            pass
        assert call_count == 1

    def test_preserves_function_name(self):
        @with_retry(max_attempts=1)
        def my_func():
            return "ok"

        assert my_func.__name__ == "my_func"

    def test_backoff_increases_delay(self):
        delays = []

        original_sleep = __import__("time").sleep

        def mock_sleep(seconds):
            delays.append(seconds)

        import time

        time.sleep = mock_sleep
        try:

            @with_retry(max_attempts=3, delay_seconds=1.0, backoff=2.0)
            def func():
                raise ValueError("always fail")

            try:
                func()
            except ValueError:
                pass

            assert delays == [1.0, 2.0]
        finally:
            time.sleep = original_sleep


class TestSafeExecute:
    def test_returns_result_on_success(self):
        result = safe_execute(lambda: 42)
        assert result == 42

    def test_returns_default_on_error(self):
        result = safe_execute(lambda: 1 / 0, default=-1)
        assert result == -1

    def test_returns_none_on_error_no_default(self):
        result = safe_execute(lambda: 1 / 0)
        assert result is None

    def test_passes_args(self):
        result = safe_execute(lambda x, y: x + y, 1, 2)
        assert result == 3

    def test_passes_kwargs(self):
        result = safe_execute(lambda *, a, b: a * b, a=3, b=4)
        assert result == 12
