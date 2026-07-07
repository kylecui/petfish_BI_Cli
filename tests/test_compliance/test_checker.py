from __future__ import annotations

from petfish_bi_cli.compliance.checker import (
    ComplianceConfig,
    ConfigLoader,
    SlaConfig,
    check_data_locality,
    generate_compliance_report,
    redact_pii,
)


class TestComplianceConfig:
    def test_defaults(self):
        cfg = ComplianceConfig()
        assert cfg.data_retention_days == 90
        assert cfg.user_consent_required is True
        assert cfg.cross_border_transfer is False
        assert cfg.data_locality == "CN"
        assert cfg.pii_redaction is True

    def test_custom_values(self):
        cfg = ComplianceConfig(
            data_retention_days=30,
            cross_border_transfer=True,
            data_locality="US",
        )
        assert cfg.data_retention_days == 30
        assert cfg.cross_border_transfer is True
        assert cfg.data_locality == "US"


class TestSlaConfig:
    def test_defaults(self):
        cfg = SlaConfig()
        assert cfg.availability_target == 99.5
        assert cfg.rate_limit_per_minute == 30
        assert cfg.max_concurrent_jobs == 10

    def test_custom_values(self):
        cfg = SlaConfig(
            availability_target=99.9,
            rate_limit_per_minute=100,
            max_concurrent_jobs=50,
        )
        assert cfg.availability_target == 99.9
        assert cfg.rate_limit_per_minute == 100


class TestConfigLoader:
    def test_load_compliance_from_yaml(self, tmp_path):
        yml = tmp_path / "bi_cli.yml"
        yml.write_text(
            "compliance:\n  data_retention_days: 60\n  data_locality: CN\n",
            encoding="utf-8",
        )
        loader = ConfigLoader(str(yml))
        cfg = loader.load_compliance()
        assert cfg.data_retention_days == 60

    def test_load_sla_from_yaml(self, tmp_path):
        yml = tmp_path / "bi_cli.yml"
        yml.write_text(
            "sla:\n  availability_target: 99.9\n  rate_limit_per_minute: 100\n",
            encoding="utf-8",
        )
        loader = ConfigLoader(str(yml))
        cfg = loader.load_sla()
        assert cfg.availability_target == 99.9
        assert cfg.rate_limit_per_minute == 100

    def test_missing_file_returns_defaults(self):
        loader = ConfigLoader("nonexistent.yml")
        cfg = loader.load_compliance()
        assert cfg.data_retention_days == 90


class TestPiiRedaction:
    def test_redacts_phone(self):
        result = redact_pii("联系我13912345678")
        assert "13912345678" not in result
        assert "[手机号已脱敏]" in result

    def test_redacts_email(self):
        result = redact_pii("邮箱user@example.com")
        assert "user@example.com" not in result
        assert "[邮箱已脱敏]" in result

    def test_redacts_id_card(self):
        result = redact_pii("身份证110101199001011234")
        assert "110101199001011234" not in result
        assert "[身份证已脱敏]" in result

    def test_preserves_normal_text(self):
        text = "CROCS洞洞鞋穿着舒服"
        assert redact_pii(text) == text

    def test_redacts_multiple_types(self):
        text = "电话13912345678邮箱test@x.com卡号6222020200112345678"
        result = redact_pii(text)
        assert "13912345678" not in result
        assert "test@x.com" not in result
        assert "6222020200112345678" not in result

    def test_empty_text(self):
        assert redact_pii("") == ""


class TestDataLocality:
    def test_cn_locality_always_passes(self, tmp_path):
        assert check_data_locality(tmp_path / "data.csv", "CN") is True

    def test_non_cn_locality_passes(self, tmp_path):
        assert check_data_locality(tmp_path / "data.csv", "US") is True


class TestComplianceReport:
    def test_compliant_report(self):
        cfg = ComplianceConfig()
        report = generate_compliance_report(cfg)
        assert report["status"] == "compliant"
        assert report["data_locality"] == "CN"
        assert report["pii_redaction"] is True

    def test_cross_border_review_required(self):
        cfg = ComplianceConfig(cross_border_transfer=True)
        report = generate_compliance_report(cfg)
        assert report["status"] == "review_required"

    def test_report_contains_all_fields(self):
        cfg = ComplianceConfig()
        report = generate_compliance_report(cfg)
        expected_keys = {
            "data_retention_days", "user_consent_required",
            "cross_border_transfer", "data_locality",
            "pii_redaction", "audit_log_enabled",
            "log_retention_days", "status",
        }
        assert set(report.keys()) == expected_keys
