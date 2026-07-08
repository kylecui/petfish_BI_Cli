"""ToolFactory — builds tool instances from config-driven declarations."""
from __future__ import annotations

from pathlib import Path

from petfishframework.core.contracts import Tool

from petfish_bi_cli.agent.tools.cross_source import CrossSourceComparisonTool
from petfish_bi_cli.agent.tools.cross_time import CrossTimeTool
from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.agent.tools.script import ScriptConfig, ScriptTool
from petfish_bi_cli.agent.tools.sentiment import SentimentAnalysisTool
from petfish_bi_cli.agent.tools.trend import TrendTool
from petfish_bi_cli.config.source_registry import SourceRegistry
from petfish_bi_cli.grounding.claims import ClaimsRegistry


class ToolFactory:
    """Builds tool instances from config-driven SourceRegistry."""

    @staticmethod
    def build_all(
        sources: SourceRegistry,
        registry: ClaimsRegistry,
        data_root: Path,
        scripts: dict[str, ScriptConfig] | None = None,
    ) -> tuple[Tool, ...]:
        tools: list[Tool] = [
            ExploreDataSourcesTool(sources=sources),
            LoadDataTool(sources=sources, registry=registry, data_root=data_root),
            SentimentAnalysisTool(data_root=data_root, registry=registry),
            TrendTool(data_root=data_root, registry=registry),
            CrossSourceComparisonTool(data_root=data_root, registry=registry),
            CrossTimeTool(data_root=data_root, registry=registry),
        ]
        if scripts:
            for script_id, cfg in scripts.items():
                tools.append(ScriptTool(script_id, cfg, registry))
        return tuple(tools)

    @staticmethod
    def parse_scripts_config(raw_config: dict) -> dict[str, ScriptConfig]:
        scripts_raw = raw_config.get("scripts", {})
        result: dict[str, ScriptConfig] = {}
        for script_id, spec in scripts_raw.items():
            result[script_id] = ScriptConfig(
                command=spec["command"],
                description=spec.get("description", ""),
                input_schema=spec.get("input_schema", {"type": "object", "properties": {}}),
                output_format=spec.get("output_format", "json"),
                timeout_s=spec.get("timeout_s", 30),
                risk_level=spec.get("risk_level", "medium"),
                capabilities=tuple(spec.get("capabilities", ("data:read",))),
            )
        return result
