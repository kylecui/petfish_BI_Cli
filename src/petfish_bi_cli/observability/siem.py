from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from petfishframework.observability.siem_sink import DEFAULT_REDACT_KEYS, SIEMSink

from petfish_bi_cli.compliance.pii import PII_TEXT_FIELDS, PIIRedactor

DEFAULT_SIEM_OUTPUT = Path("outputs/audit/siem.jsonl")


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
        text_fields: frozenset[str] = PII_TEXT_FIELDS,
        redactor: PIIRedactor | None = None,
    ):
        self._downstream = downstream
        self._text_fields = text_fields
        self._redactor = redactor or PIIRedactor()

    def __call__(self, event: Any) -> None:
        redacted_data = dict(event.data)
        for key in self._text_fields:
            if key in redacted_data and isinstance(redacted_data[key], str):
                redacted_data[key] = self._redactor.redact(redacted_data[key])
        from dataclasses import replace

        self._downstream(replace(event, data=redacted_data))
