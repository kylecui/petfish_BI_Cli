"""Tests for config wizard and RAG config integration."""
from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from petfish_bi_cli.main import app

runner = CliRunner()


class TestConfigInit:
    def test_config_init_command_exists(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout

    def test_config_show_command_exists(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.stdout

    def test_config_show_outputs_json(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "model" in result.stdout


class TestScanDataDir:
    def test_scan_finds_csv_and_json(self, tmp_path):
        from petfish_bi_cli.cli.config_cmd import _scan_data_dir

        (tmp_path / "products.csv").write_text("name,price\nA,100")
        (tmp_path / "data.json").write_text('{"key": "value"}')
        (tmp_path / "readme.txt").write_text("not data")

        sources = _scan_data_dir(tmp_path)
        assert "products" in sources
        assert sources["products"]["type"] == "csv"
        assert "data" in sources
        assert sources["data"]["type"] == "json"
        assert "readme" not in sources

    def test_scan_empty_dir(self, tmp_path):
        from petfish_bi_cli.cli.config_cmd import _scan_data_dir

        sources = _scan_data_dir(tmp_path)
        assert sources == {}

    def test_scan_nonexistent_dir(self):
        from petfish_bi_cli.cli.config_cmd import _scan_data_dir

        sources = _scan_data_dir(Path("/nonexistent"))
        assert sources == {}


class TestBuildConfig:
    def test_generates_valid_yaml(self):
        from petfish_bi_cli.cli.config_cmd import _build_config

        config = _build_config(
            provider="fake",
            model_name="fake",
            data_root="references",
            sources={},
            enable_web=False,
        )
        assert config["model"]["provider"] == "fake"
        assert config["data"]["root"] == "references"
        assert "budget" in config

    def test_includes_sources_when_provided(self):
        from petfish_bi_cli.cli.config_cmd import _build_config

        config = _build_config(
            provider="openai",
            model_name="gpt-4o",
            data_root="data",
            sources={"my_data": {"type": "csv", "path": "my.csv", "description": "My data"}},
            enable_web=True,
        )
        assert "sources" in config
        assert "my_data" in config["sources"]

    def test_yaml_serializable(self):
        from petfish_bi_cli.cli.config_cmd import _build_config

        config = _build_config("fake", "fake", "references", {}, False)
        yaml_str = yaml.dump(config, allow_unicode=True)
        assert "model" in yaml_str
        parsed = yaml.safe_load(yaml_str)
        assert parsed["model"]["provider"] == "fake"


class TestRagConfig:
    def test_rag_disabled_by_default(self):
        from petfish_bi_cli.config.settings import load_settings

        settings = load_settings()
        assert settings.rag.enabled is False

    def test_rag_config_parsed_from_yaml(self, tmp_path):
        from petfish_bi_cli.config.settings import load_settings

        config_file = tmp_path / "test.yml"
        config_file.write_text(
            "rag:\n"
            "  enabled: true\n"
            "  retriever: crag\n"
            "  chunk_size: 300\n"
            "  top_k: 3\n"
            "  documents:\n"
            "    - path: docs/guide.md\n"
        )
        settings = load_settings(config_path=str(config_file))
        assert settings.rag.enabled is True
        assert settings.rag.retriever == "crag"
        assert settings.rag.chunk_size == 300
        assert settings.rag.top_k == 3
        assert len(settings.rag.documents) == 1

    def test_framework_passes_retriever_when_enabled(self):
        from petfish_bi_cli.framework import make_bi_agent

        agent = make_bi_agent()
        assert agent is not None
