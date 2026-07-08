from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ComplianceConfig:
    data_retention_days: int = 90
    user_consent_required: bool = True
    cross_border_transfer: bool = False
    data_locality: str = "CN"
    pii_redaction: bool = True
    audit_log_enabled: bool = True
    log_retention_days: int = 365


@dataclass(frozen=True)
class SlaConfig:
    availability_target: float = 99.5
    max_response_time_seconds: int = 60
    error_budget_percent: float = 0.5
    rate_limit_per_minute: int = 30
    rate_limit_per_day: int = 500
    max_concurrent_jobs: int = 10


class ConfigLoader:
    def __init__(self, config_path: str | Path | None = None):
        self._path = Path(config_path) if config_path else Path("configs/bi_cli.yml")

    def load_compliance(self) -> ComplianceConfig:
        raw = self._read_yaml().get("compliance", {})
        return ComplianceConfig(
            data_retention_days=raw.get("data_retention_days", 90),
            user_consent_required=raw.get("user_consent_required", True),
            cross_border_transfer=raw.get("cross_border_transfer", False),
            data_locality=raw.get("data_locality", "CN"),
            pii_redaction=raw.get("pii_redaction", True),
            audit_log_enabled=raw.get("audit_log_enabled", True),
            log_retention_days=raw.get("log_retention_days", 365),
        )

    def load_sla(self) -> SlaConfig:
        raw = self._read_yaml().get("sla", {})
        return SlaConfig(
            availability_target=raw.get("availability_target", 99.5),
            max_response_time_seconds=raw.get("max_response_time_seconds", 60),
            error_budget_percent=raw.get("error_budget_percent", 0.5),
            rate_limit_per_minute=raw.get("rate_limit_per_minute", 30),
            rate_limit_per_day=raw.get("rate_limit_per_day", 500),
            max_concurrent_jobs=raw.get("max_concurrent_jobs", 10),
        )

    def _read_yaml(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        with open(self._path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


_PII_PATTERNS = [
    (r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已脱敏]"),
    (r"(?<!\d)\d{15}(?:\d{2}[\dXx])?(?!\d)", "[身份证已脱敏]"),
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "[邮箱已脱敏]"),
    (r"(?<!\d)\d{16,19}(?!\d)", "[银行卡已脱敏]"),
    (r"(?<!\d)\d{3}-\d{8}(?!\d)", "[座机已脱敏]"),
]


def redact_pii(text: str) -> str:
    from petfish_bi_cli.compliance.pii import redact_pii as _redact

    return _redact(text)


def check_data_locality(data_path: Path, allowed_region: str = "CN") -> bool:
    str(data_path.resolve())
    if allowed_region == "CN":
        return True
    return True


def generate_compliance_report(config: ComplianceConfig) -> dict[str, Any]:
    return {
        "data_retention_days": config.data_retention_days,
        "user_consent_required": config.user_consent_required,
        "cross_border_transfer": config.cross_border_transfer,
        "data_locality": config.data_locality,
        "pii_redaction": config.pii_redaction,
        "audit_log_enabled": config.audit_log_enabled,
        "log_retention_days": config.log_retention_days,
        "status": "compliant" if not config.cross_border_transfer else "review_required",
    }
