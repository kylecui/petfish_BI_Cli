"""Centralized PII redaction — single source of truth for all PII scrubbing.

All modules that need PII redaction should import from here, not from
compliance/checker.py (which now re-exports for backward compatibility).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PIIPattern:
    regex: str
    replacement: str
    name: str = ""


DEFAULT_PII_PATTERNS: tuple[PIIPattern, ...] = (
    PIIPattern(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已脱敏]", "phone"),
    PIIPattern(r"(?<!\d)\d{15}(?:\d{2}[\dXx])?(?!\d)", "[身份证已脱敏]", "id_card"),
    PIIPattern(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[邮箱已脱敏]", "email"),
    PIIPattern(r"(?<!\d)\d{16,19}(?!\d)", "[银行卡已脱敏]", "bank_card"),
    PIIPattern(r"(?<!\d)\d{3}-\d{8}(?!\d)", "[座机已脱敏]", "landline"),
)


@dataclass
class PIIRedactor:
    patterns: tuple[PIIPattern, ...] = field(default_factory=lambda: DEFAULT_PII_PATTERNS)
    _compiled: tuple = field(default=(), repr=False)

    def __post_init__(self) -> None:
        self._compiled = tuple(
            (re.compile(p.regex), p.replacement) for p in self.patterns
        )

    def redact(self, text: str) -> str:
        for regex, replacement in self._compiled:
            text = regex.sub(replacement, text)
        return text


_default_redactor = PIIRedactor()


def redact_pii(text: str) -> str:
    return _default_redactor.redact(text)


PII_TEXT_FIELDS: frozenset[str] = frozenset({
    "task",
    "query",
    "answer",
    "prompt",
    "reason",
})
