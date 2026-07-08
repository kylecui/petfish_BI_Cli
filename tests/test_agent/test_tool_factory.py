"""Tests for ToolFactory and framework wiring with SourceRegistry."""
from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tool_factory import ToolFactory
from petfish_bi_cli.config.source_registry import SourceRegistry
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"

_CONFIG_WITH_SOURCES = {
    "sources": {
        "jd_products": {
            "type": "json",
            "path": "JD_CROCS_Raw_Memory_Dump.json",
            "description": "京东CROCS商品",
            "metrics": [
                {"name": "avg_price", "column": "calculatedFinalPrice", "aggregation": "avg"},
            ],
        },
    },
}


class TestToolFactory:
    def test_build_all_creates_all_builtin_tools(self):
        sources = SourceRegistry(config={}, data_root=DATA_ROOT)
        tools = ToolFactory.build_all(
            sources=sources, registry=ClaimsRegistry(), data_root=DATA_ROOT,
        )
        names = [t.name for t in tools]
        assert "explore_data_sources" in names
        assert "load_data" in names
        assert "analyze_sentiment" in names
        assert "analyze_trend" in names
        assert "compare_sources" in names
        assert "cross_time_compare" in names

    def test_build_all_returns_tuple(self):
        sources = SourceRegistry(config={}, data_root=DATA_ROOT)
        tools = ToolFactory.build_all(
            sources=sources, registry=ClaimsRegistry(), data_root=DATA_ROOT,
        )
        assert isinstance(tools, tuple)
        assert len(tools) >= 6

    def test_build_all_uses_source_registry(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tools = ToolFactory.build_all(
            sources=sources, registry=ClaimsRegistry(), data_root=DATA_ROOT,
        )
        load_tool = next(t for t in tools if t.name == "load_data")
        result = load_tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert result.error is None

    def test_build_all_explore_uses_source_registry(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tools = ToolFactory.build_all(
            sources=sources, registry=ClaimsRegistry(), data_root=DATA_ROOT,
        )
        explore_tool = next(t for t in tools if t.name == "explore_data_sources")
        result = explore_tool.execute({})
        assert result.value["count"] >= 1


class TestFrameworkWiring:
    def test_make_bi_agent_returns_agent(self):
        from petfish_bi_cli.framework import make_bi_agent

        agent = make_bi_agent()
        assert agent is not None

    def test_make_bi_agent_has_tools(self):
        from petfish_bi_cli.framework import make_bi_agent

        agent = make_bi_agent()
        names = [t.name for t in agent.tools]
        assert "explore_data_sources" in names
        assert "load_data" in names

    def test_make_bi_agent_uses_tool_factory(self):
        from petfish_bi_cli.framework import make_bi_agent

        agent = make_bi_agent()
        assert len(agent.tools) >= 6

    def test_make_bi_agent_with_sources_config(self):
        from petfish_bi_cli.config.settings import load_settings
        from petfish_bi_cli.framework import make_bi_agent

        settings = load_settings()
        agent = make_bi_agent(settings=settings)
        explore = next(t for t in agent.tools if t.name == "explore_data_sources")
        result = explore.execute({})
        assert result.error is None
        assert result.value["count"] > 0
