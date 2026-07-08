from __future__ import annotations

import pytest

from petfish_bi_cli.config.settings import (
    load_settings,
)


class TestLoadSettings:
    def test_loads_defaults_when_no_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BI_CLI_CONFIG", raising=False)
        settings = load_settings()
        assert settings.model.provider == "fake"
        assert settings.budget.max_steps == 25
        assert settings.data.root == "references"

    def test_loads_yaml_config(self, tmp_path):
        config = tmp_path / "bi_cli.yml"
        config.write_text(
            "model:\n"
            "  provider: openai\n"
            "  name: gpt-4o\n"
            "  temperature: 0.3\n"
            "budget:\n"
            "  max_steps: 50\n"
        )
        settings = load_settings(config)
        assert settings.model.provider == "openai"
        assert settings.model.name == "gpt-4o"
        assert settings.model.temperature == 0.3
        assert settings.budget.max_steps == 50

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config = tmp_path / "bi_cli.yml"
        config.write_text("model:\n  provider: openai\n  name: gpt-4o\n")
        monkeypatch.setenv("BI_CLI_MODEL_NAME", "gpt-4o-mini")
        settings = load_settings(config)
        assert settings.model.name == "gpt-4o-mini"
        assert settings.model.provider == "openai"

    def test_env_temperature_parsed_as_float(self, tmp_path, monkeypatch):
        config = tmp_path / "bi_cli.yml"
        config.write_text("model:\n  provider: fake\n")
        monkeypatch.setenv("BI_CLI_MODEL_TEMPERATURE", "0.7")
        settings = load_settings(config)
        assert settings.model.temperature == 0.7

    def test_roles_loaded(self, tmp_path):
        config = tmp_path / "bi_cli.yml"
        config.write_text(
            "model:\n  provider: fake\n"
            "roles:\n"
            "  primary:\n    provider: anthropic\n    name: claude-sonnet-4-5-20250929\n"
            "  fallback:\n    provider: openai\n    name: gpt-4o-mini\n"
            "  testing:\n    provider: fake\n"
        )
        settings = load_settings(config)
        assert settings.roles["primary"].provider == "anthropic"
        assert settings.roles["fallback"].name == "gpt-4o-mini"
        assert settings.primary_model.provider == "anthropic"
        assert settings.fallback_model is not None
        assert settings.fallback_model.name == "gpt-4o-mini"

    def test_data_config(self, tmp_path):
        config = tmp_path / "bi_cli.yml"
        config.write_text("data:\n  root: /custom/data\n  semantic_dir: /custom/sem\n")
        settings = load_settings(config)
        assert settings.data.root == "/custom/data"
        assert settings.data.semantic_dir == "/custom/sem"

    def test_deep_merge_preserves_defaults(self, tmp_path):
        config = tmp_path / "bi_cli.yml"
        config.write_text("model:\n  provider: openai\n")
        settings = load_settings(config)
        assert settings.model.provider == "openai"
        assert settings.model.temperature == 0.0
        assert settings.budget.max_cost_usd == 0.50

    def test_bi_cli_config_env_var(self, tmp_path, monkeypatch):
        config = tmp_path / "custom.yml"
        config.write_text("model:\n  provider: anthropic\n")
        monkeypatch.setenv("BI_CLI_CONFIG", str(config))
        settings = load_settings()
        assert settings.model.provider == "anthropic"

    def test_openai_api_key_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-standard-key")
        monkeypatch.chdir(tmp_path)
        settings = load_settings()
        assert settings.model.api_key == "sk-standard-key"

    def test_anthropic_api_key_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("BI_CLI_MODEL_PROVIDER", "anthropic")
        monkeypatch.chdir(tmp_path)
        settings = load_settings()
        assert settings.model.api_key == "sk-ant-key"

    @pytest.mark.dotenv
    def test_dotenv_file_loaded(self, tmp_path, monkeypatch):
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text("OPENAI_API_KEY=sk-from-dotenv\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        settings = load_settings()
        assert settings.model.api_key == "sk-from-dotenv"

    def test_yaml_api_key_overrides_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
        config = tmp_path / "bi_cli.yml"
        config.write_text("model:\n  provider: openai\n  api_key: sk-from-yaml\n")
        settings = load_settings(config)
        assert settings.model.api_key == "sk-from-yaml"
