"""Tests for ExploreDataSourcesTool with SourceRegistry integration."""
from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.config.source_registry import SourceRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"

_CONFIG_WITH_SOURCES = {
    "sources": {
        "jd_products": {
            "path": "mock_jd_products.json",
            "description": "JD products",
            "metrics": [
                {"name": "avg_price", "column": "calculatedFinalPrice", "aggregation": "avg"},
                {"name": "product_count", "aggregation": "count"},
            ],
        },
        "tmall_products": {
            "path": "mock_tmall_products.json",
            "description": "TMALL products",
        },
    },
}


class TestExploreWithSourceRegistry:
    def test_accepts_source_registry(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tool = ExploreDataSourcesTool(sources=sources)
        assert tool.name == "explore_data_sources"

    def test_returns_all_config_sources(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tool = ExploreDataSourcesTool(sources=sources)
        result = tool.execute({})
        assert result.error is None
        assert result.value["count"] == 2
        source_ids = [s["source_id"] for s in result.value["sources"]]
        assert "jd_products" in source_ids
        assert "tmall_products" in source_ids

    def test_single_source_detail(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tool = ExploreDataSourcesTool(sources=sources)
        result = tool.execute({"source_id": "jd_products"})
        assert result.error is None
        assert result.value["source_id"] == "jd_products"
        assert "avg_price" in result.value["metrics"]

    def test_unknown_source_detail(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tool = ExploreDataSourcesTool(sources=sources)
        result = tool.execute({"source_id": "nonexistent"})
        assert result.error is not None

    def test_backward_compat_semantic_dir(self):
        tool = ExploreDataSourcesTool(semantic_dir=DATA_ROOT / "semantic")
        result = tool.execute({})
        assert result.error is None
        assert result.value["count"] > 0

    def test_protocol_attributes(self):
        sources = SourceRegistry(config={}, data_root=DATA_ROOT)
        tool = ExploreDataSourcesTool(sources=sources)
        assert tool.capabilities == ("data:read",)
        assert tool.side_effect is False
