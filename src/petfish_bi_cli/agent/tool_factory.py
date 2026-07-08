"""ToolFactory — builds tool instances from config-driven declarations."""
from __future__ import annotations

from pathlib import Path

from petfishframework.core.contracts import Tool

from petfish_bi_cli.agent.tools.cross_source import CrossSourceComparisonTool
from petfish_bi_cli.agent.tools.cross_time import CrossTimeTool
from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.agent.tools.load import LoadDataTool
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
    ) -> tuple[Tool, ...]:
        tools: list[Tool] = [
            ExploreDataSourcesTool(sources=sources),
            LoadDataTool(sources=sources, registry=registry, data_root=data_root),
            SentimentAnalysisTool(data_root=data_root, registry=registry),
            TrendTool(data_root=data_root, registry=registry),
            CrossSourceComparisonTool(data_root=data_root, registry=registry),
            CrossTimeTool(data_root=data_root, registry=registry),
        ]
        return tuple(tools)
