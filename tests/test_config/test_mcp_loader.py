from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from petfish_bi_cli.config.mcp_loader import MCPLoader, _resolve_env


class TestResolveEnv:
    def test_resolves_existing_var(self, monkeypatch):
        monkeypatch.setenv("MY_API_KEY", "sk-test-123")
        result = _resolve_env({"API_KEY": "${MY_API_KEY}"})
        assert result["API_KEY"] == "sk-test-123"

    def test_missing_var_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        result = _resolve_env({"KEY": "${NONEXISTENT_VAR}"})
        assert result["KEY"] == ""

    def test_no_vars_passthrough(self):
        result = _resolve_env({"KEY": "static_value"})
        assert result["KEY"] == "static_value"

    def test_mixed_vars(self, monkeypatch):
        monkeypatch.setenv("VAR1", "resolved")
        result = _resolve_env({"A": "${VAR1}", "B": "static"})
        assert result["A"] == "resolved"
        assert result["B"] == "static"


class TestMCPLoader:
    def test_empty_config_path_returns_empty(self, tmp_path):
        loader = MCPLoader(config_path=str(tmp_path / "nonexistent.yml"))
        assert loader.load() == []

    def test_no_servers_returns_empty(self, tmp_path):
        config_file = tmp_path / "mcp.yml"
        config_file.write_text("auto_load: true\n", encoding="utf-8")
        loader = MCPLoader(config_path=str(config_file))
        assert loader.load() == []

    def test_auto_load_false_returns_empty(self, tmp_path):
        config_file = tmp_path / "mcp.yml"
        config_file.write_text(
            'auto_load: false\nservers:\n  fs:\n    command: npx\n    args: []\n',
            encoding="utf-8",
        )
        loader = MCPLoader(config_path=str(config_file))
        assert loader.load() == []

    @patch("petfish_bi_cli.config.mcp_loader.connect_stdio")
    def test_loads_stdio_server(self, mock_connect, tmp_path):
        mock_client = MagicMock()
        mock_client.discover_tools.return_value = [MagicMock(name="tool1")]
        mock_connect.return_value = mock_client

        config_file = tmp_path / "mcp.yml"
        config_file.write_text(
            'auto_load: true\nservers:\n  filesystem:\n    command: npx\n    args:\n      - "-y"\n      - "server-fs"\n',
            encoding="utf-8",
        )
        loader = MCPLoader(config_path=str(config_file))
        tools = loader.load()
        assert len(tools) == 1
        mock_connect.assert_called_once()

    @patch("petfish_bi_cli.config.mcp_loader.connect_stdio")
    def test_passes_env_to_connect(self, mock_connect, monkeypatch, tmp_path):
        monkeypatch.setenv("TOKEN", "secret123")
        mock_client = MagicMock()
        mock_client.discover_tools.return_value = []
        mock_connect.return_value = mock_client

        config_file = tmp_path / "mcp.yml"
        config_file.write_text(
            'auto_load: true\nservers:\n  db:\n    command: npx\n    args:\n      - "server"\n    env:\n      DB_TOKEN: "${TOKEN}"\n',
            encoding="utf-8",
        )
        loader = MCPLoader(config_path=str(config_file))
        loader.load()
        call_kwargs = mock_connect.call_args
        assert call_kwargs.kwargs["env"]["DB_TOKEN"] == "secret123"

    @patch("petfish_bi_cli.config.mcp_loader.connect_stdio")
    def test_skips_on_connection_error(self, mock_connect, tmp_path):
        mock_connect.side_effect = ConnectionError("server not found")

        config_file = tmp_path / "mcp.yml"
        config_file.write_text(
            'auto_load: true\nservers:\n  bad:\n    command: "nonexistent"\n    args: []\n',
            encoding="utf-8",
        )
        loader = MCPLoader(config_path=str(config_file))
        assert loader.load() == []

    @patch("petfish_bi_cli.config.mcp_loader.connect_stdio")
    def test_loads_multiple_servers(self, mock_connect, tmp_path):
        mock_client = MagicMock()
        mock_client.discover_tools.return_value = [MagicMock(), MagicMock()]
        mock_connect.return_value = mock_client

        config_file = tmp_path / "mcp.yml"
        config_file.write_text(
            'auto_load: true\nservers:\n  fs:\n    command: npx\n    args:\n      - "fs"\n  db:\n    command: npx\n    args:\n      - "db"\n',
            encoding="utf-8",
        )
        loader = MCPLoader(config_path=str(config_file))
        tools = loader.load()
        assert len(tools) == 4
        assert mock_connect.call_count == 2

    def test_cleanup_does_not_crash_on_empty(self):
        loader = MCPLoader(config_path="nonexistent.yml")
        loader.cleanup()
