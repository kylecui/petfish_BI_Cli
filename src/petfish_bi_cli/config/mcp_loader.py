from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from petfishframework.core.contracts import Tool
from petfishframework.mcp.client import connect_stdio


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    url: str | None = None
    headers: dict[str, str] | None = None
    description: str = ""


@dataclass
class MCPLoader:
    """Reads MCP server configs from YAML and connects to servers.

    Usage:
        loader = MCPLoader("configs/mcp.yml")
        tools = loader.load()
        # ... use tools in Agent ...
        loader.cleanup()
    """

    config_path: str | Path = "configs/mcp.yml"
    _clients: list[Any] = field(default_factory=list, repr=False)

    def load(self) -> list[Tool]:
        if not Path(self.config_path).exists():
            return []

        with open(self.config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        servers = raw.get("mcp_servers", raw.get("mcpServers", raw.get("servers", {})))
        if not servers:
            return []

        auto_load = raw.get("auto_load", True)
        if not auto_load:
            return []

        tools: list[Tool] = []
        for name, cfg in servers.items():
            server = self._parse_server(name, cfg)
            if server.transport == "stdio":
                server_tools = self._connect_stdio(server)
                tools.extend(server_tools)
        return tools

    def _parse_server(self, name: str, cfg: dict) -> MCPServerConfig:
        return MCPServerConfig(
            name=name,
            command=cfg.get("command", ""),
            args=cfg.get("args", []),
            env=_resolve_env(cfg.get("env", {})),
            transport=cfg.get("transport", "stdio"),
            url=cfg.get("url"),
            headers=cfg.get("headers"),
            description=cfg.get("description", ""),
        )

    def _connect_stdio(self, server: MCPServerConfig) -> list[Tool]:
        try:
            client = connect_stdio(
                command=server.command,
                args=server.args,
                env=server.env or None,
            )
            self._clients.append(client)
            return client.discover_tools()
        except Exception:
            return []

    def cleanup(self) -> None:
        for client in self._clients:
            transport = getattr(client, "_transport", None)
            if transport and hasattr(transport, "close"):
                try:
                    transport.close()
                except Exception:
                    pass
        self._clients.clear()


def _resolve_env(env: dict[str, str]) -> dict[str, str]:
    pattern = re.compile(r"\$\{(\w+)(?::-(.*?))?\}")

    def replacer(m: re.Match) -> str:
        var_name = m.group(1)
        default = m.group(2) or ""
        return os.environ.get(var_name, default)

    return {k: pattern.sub(replacer, v) for k, v in env.items()}
