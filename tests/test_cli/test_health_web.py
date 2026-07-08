"""Tests for petfish-bi health and web CLI commands."""
from __future__ import annotations

from typer.testing import CliRunner

from petfish_bi_cli.main import app

runner = CliRunner()


class TestHealthCommand:
    def test_health_exits_0_when_config_valid(self):
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "status" in result.stdout.lower() or "ok" in result.stdout.lower()

    def test_health_outputs_json(self):
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "{" in result.stdout or "ok" in result.stdout.lower()


class TestWebCommand:
    def test_web_command_exists(self):
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        assert "host" in result.stdout.lower() or "port" in result.stdout.lower()

    def test_web_command_help_shows_options(self):
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.stdout or "--port" in result.stdout


class TestExistingCommandsPreserved:
    def test_ask_command_still_exists(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ask" in result.stdout

    def test_sources_command_still_exists(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sources" in result.stdout
