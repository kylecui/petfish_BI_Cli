from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from petfishframework.observability.siem_sink import DEFAULT_REDACT_KEYS, SIEMSink

from petfish_bi_cli.compliance.checker import redact_pii

DEFAULT_SIEM_OUTPUT = Path("outputs/audit/siem.jsonl")

_PII_TEXT_FIELDS = frozenset({"task", "query", "answer", "prompt", "reason"})


def make_siem_sink(
    output_path: str | Path | None = None,
    extra_redact_keys: tuple[str, ...] = (),
) -> SIEMSink:
    """Create a SIEMSink with BI-specific redaction defaults."""
    path = str(output_path) if output_path is not None else str(DEFAULT_SIEM_OUTPUT)
    return SIEMSink(
        output_path=path,
        redact_keys=DEFAULT_REDACT_KEYS | frozenset(extra_redact_keys),
    )


class PIIRedactingSink:
    """Wrapper that redacts PII from free-text event fields, then forwards to a downstream sink."""

    def __init__(
        self,
        downstream: Callable[[Any], None],
        text_fields: frozenset[str] = _PII_TEXT_FIELDS,
    ):
        self._downstream = downstream
        self._text_fields = text_fields

    def __call__(self, event: Any) -> None:
        redacted_data = _redact_text_fields(event.data, self._text_fields)
        redacted_event = _replace_event_data(event, redacted_data)
        self._downstream(redacted_event)


def _redact_text_fields(data: dict[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    result = dict(data)
    for key in fields:
        if key in result and isinstance(result[key], str):
            result[key] = redact_pii(result[key])
    return result


def _replace_event_data(event: Any, new_data: dict[str, Any]) -> Any:
    from dataclasses import replace

    return replace(event, data=new_data)
