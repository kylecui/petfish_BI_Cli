from __future__ import annotations

from typer.testing import CliRunner

from petfish_bi_cli.main import app

runner = CliRunner()


class TestCLI:
    def test_sources_command(self):
        result = runner.invoke(app, ["sources"])
        assert result.exit_code == 0
        assert "jd_products" in result.output or "tmall_products" in result.output

    def test_ask_command_help(self):
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--data-source" in result.output
