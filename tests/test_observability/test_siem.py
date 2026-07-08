"""Tests for SIEMSink integration with PII redaction wrapper."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from petfishframework.core.events import Event
from petfishframework.observability.siem_sink import SIEMSink

from petfish_bi_cli.observability.siem import PIIRedactingSink, make_siem_sink


class TestMakeSiemSink:
    def test_creates_siem_sink_with_file_output(self, tmp_path):
        output = tmp_path / "siem.jsonl"
        sink = make_siem_sink(output_path=output)
        assert isinstance(sink, SIEMSink)
        assert output.parent.exists()

    def test_default_output_path(self):
        sink = make_siem_sink()
        assert isinstance(sink, SIEMSink)

    def test_extra_redact_keys(self, tmp_path):
        sink = make_siem_sink(
            output_path=tmp_path / "siem.jsonl",
            extra_redact_keys=("custom_secret",),
        )
        assert isinstance(sink, SIEMSink)


class TestPIIRedactingSink:
    def test_redacts_phone_from_task_field(self):
        downstream = MagicMock()
        wrapper = PIIRedactingSink(downstream)
        event = Event(
            type="session.start",
            timestamp=0.0,
            data={"task": "联系我13912345678", "session_id": "abc"},
        )
        wrapper(event)
        forwarded = downstream.call_args[0][0]
        assert "13912345678" not in forwarded.data["task"]
        assert "[手机号已脱敏]" in forwarded.data["task"]

    def test_redacts_email_from_query_field(self):
        downstream = MagicMock()
        wrapper = PIIRedactingSink(downstream)
        event = Event(
            type="tool.called",
            timestamp=0.0,
            data={"query": "发到user@example.com", "tool_name": "load_data"},
        )
        wrapper(event)
        forwarded = downstream.call_args[0][0]
        assert "user@example.com" not in forwarded.data["query"]

    def test_preserves_non_text_fields(self):
        downstream = MagicMock()
        wrapper = PIIRedactingSink(downstream)
        event = Event(
            type="tool.called",
            timestamp=0.0,
            data={"tool_name": "explore_data_sources", "duration_ms": 42.5},
        )
        wrapper(event)
        forwarded = downstream.call_args[0][0]
        assert forwarded.data["tool_name"] == "explore_data_sources"
        assert forwarded.data["duration_ms"] == 42.5

    def test_preserves_non_pii_text(self):
        downstream = MagicMock()
        wrapper = PIIRedactingSink(downstream)
        event = Event(
            type="session.start",
            timestamp=0.0,
            data={"task": "CROCS在京东的均价是多少？"},
        )
        wrapper(event)
        forwarded = downstream.call_args[0][0]
        assert forwarded.data["task"] == "CROCS在京东的均价是多少？"

    def test_downstream_called_exactly_once(self):
        downstream = MagicMock()
        wrapper = PIIRedactingSink(downstream)
        event = Event(type="test", timestamp=0.0, data={"task": "hello"})
        wrapper(event)
        assert downstream.call_count == 1


class TestSIEMSinkIntegration:
    def test_siem_sink_writes_jsonl_file(self, tmp_path):
        output = tmp_path / "siem.jsonl"
        sink = SIEMSink(output_path=str(output))
        event = Event(
            type="tool.called",
            timestamp=1234567890.0,
            data={"tool_name": "load_data", "executed": True, "effect": "allow"},
        )
        sink(event)
        sink.close()
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["event_type"] == "tool.called"
        assert record["tool_name"] == "load_data"

    def test_siem_sink_redacts_credential_token(self, tmp_path):
        output = tmp_path / "siem.jsonl"
        sink = SIEMSink(output_path=str(output))
        event = Event(
            type="tool.called",
            timestamp=0.0,
            data={
                "tool_name": "load_data",
                "args": {"_credential_token": {"token_id": "abc", "tool_name": "load_data"}},
            },
        )
        sink(event)
        sink.close()
        record = json.loads(output.read_text().strip())
        assert record["details"]["args"]["_credential_token"]["redacted"] is True

    def test_pii_wrapper_then_siem_end_to_end(self, tmp_path):
        output = tmp_path / "siem.jsonl"
        siem = SIEMSink(output_path=str(output))
        wrapper = PIIRedactingSink(siem)
        event = Event(
            type="session.start",
            timestamp=0.0,
            data={"task": "手机13912345678查询CROCS价格"},
        )
        wrapper(event)
        siem.close()
        record = json.loads(output.read_text().strip())
        assert "13912345678" not in record["details"]["task"]
        assert "[手机号已脱敏]" in record["details"]["task"]
