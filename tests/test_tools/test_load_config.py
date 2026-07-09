"""Tests for LoadDataTool with SourceRegistry integration."""
from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.config.source_registry import SourceRegistry
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"

_CONFIG_WITH_SOURCES = {
    "sources": {
        "jd_products": {
            "type": "json",
            "path": "mock_jd_products.json",
            "description": "京东CROCS商品",
            "file_pattern": "mock_jd_products.json",
            "metrics": [
                {"name": "avg_price", "column": "calculatedFinalPrice", "aggregation": "avg"},
                {"name": "product_count", "aggregation": "count"},
            ],
        },
    },
}


class TestLoadDataToolSourceRegistry:
    def test_accepts_source_registry(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        tool = LoadDataTool(sources=sources, registry=ClaimsRegistry())
        assert tool.name == "load_data"

    def test_load_with_source_registry(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        reg = ClaimsRegistry()
        tool = LoadDataTool(sources=sources, registry=reg)
        result = tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0

    def test_backward_compat_data_root_constructor(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0

    def test_metric_avg_from_metric_spec(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        reg = ClaimsRegistry()
        tool = LoadDataTool(sources=sources, registry=reg)
        result = tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert result.error is None
        claim_value = result.value["claims"][0]["value"]
        assert claim_value > 0

    def test_metric_count_from_metric_spec(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        reg = ClaimsRegistry()
        tool = LoadDataTool(sources=sources, registry=reg)
        result = tool.execute({"source": "jd_products", "metric": "product_count"})
        assert result.error is None
        assert result.value["claims"][0]["value"] == 4.0

    def test_unknown_source_with_registry(self):
        sources = SourceRegistry(config={}, data_root=DATA_ROOT)
        tool = LoadDataTool(sources=sources, registry=ClaimsRegistry())
        result = tool.execute({"source": "nonexistent"})
        assert result.error is not None

    def test_registry_gets_claim(self):
        sources = SourceRegistry(config=_CONFIG_WITH_SOURCES, data_root=DATA_ROOT)
        reg = ClaimsRegistry()
        tool = LoadDataTool(sources=sources, registry=reg)
        tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert reg.count == 1

    def test_protocol_attributes_preserved(self):
        sources = SourceRegistry(config={}, data_root=DATA_ROOT)
        tool = LoadDataTool(sources=sources, registry=ClaimsRegistry())
        assert tool.capabilities == ("data:read",)
        assert tool.side_effect is False
        assert tool.idempotent is True
