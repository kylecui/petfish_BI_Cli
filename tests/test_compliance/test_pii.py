"""Tests for centralized PII redaction module."""
from __future__ import annotations

from petfish_bi_cli.compliance.pii import (
    PII_TEXT_FIELDS,
    PIIRedactor,
    redact_pii,
)


class TestRedactPii:
    def test_redacts_phone(self):
        assert "[手机号已脱敏]" in redact_pii("联系我13912345678")

    def test_redacts_email(self):
        assert "[邮箱已脱敏]" in redact_pii("发到user@example.com")

    def test_redacts_id_card(self):
        assert "[身份证已脱敏]" in redact_pii("身份证110101199001011234")

    def test_redacts_bank_card(self):
        assert "[银行卡已脱敏]" in redact_pii("卡号6222021234567890123")

    def test_preserves_non_pii_text(self):
        text = "CROCS在京东的均价是多少？"
        assert redact_pii(text) == text

    def test_multiple_pii_in_one_string(self):
        result = redact_pii("手机13912345678邮箱test@test.com")
        assert "13912345678" not in result
        assert "test@test.com" not in result
        assert "[手机号已脱敏]" in result
        assert "[邮箱已脱敏]" in result

    def test_empty_string(self):
        assert redact_pii("") == ""


class TestPIIRedactor:
    def test_default_patterns(self):
        redactor = PIIRedactor()
        assert "[手机号已脱敏]" in redactor.redact("电话13912345678")

    def test_custom_patterns(self):
        from petfish_bi_cli.compliance.pii import PIIPattern

        custom = PIIRedactor(patterns=(PIIPattern(r"\bTODO\b", "[TODO]"),))
        assert "[TODO]" in custom.redact("fix this TODO later")
        assert "13912345678" in custom.redact("13912345678")

    def test_no_double_redaction(self):
        result = redact_pii("[手机号已脱敏]")
        assert result == "[手机号已脱敏]"


class TestPIITextFields:
    def test_includes_task_and_query(self):
        assert "task" in PII_TEXT_FIELDS
        assert "query" in PII_TEXT_FIELDS

    def test_includes_answer(self):
        assert "answer" in PII_TEXT_FIELDS


class TestCheckerBackwardCompat:
    def test_checker_re_exports_redact_pii(self):
        from petfish_bi_cli.compliance.checker import redact_pii as checker_redact

        assert "[手机号已脱敏]" in checker_redact("13912345678")
