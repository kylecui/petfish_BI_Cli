from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.cross_source import CrossSourceComparisonTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestCrossSourceComparison:
    def test_jd_vs_tmall_avg_price(self):
        reg = ClaimsRegistry()
        tool = CrossSourceComparisonTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({
            "sources": ["jd_products", "tmall_products"],
            "metric": "avg_price",
        })
        assert result.error is None
        assert "jd_products" in result.value["comparison"]
        assert "tmall_products" in result.value["comparison"]
        assert "difference" in result.value
        assert result.value["difference"]["absolute"] != 0

    def test_writes_claims_to_registry(self):
        reg = ClaimsRegistry()
        tool = CrossSourceComparisonTool(data_root=DATA_ROOT, registry=reg)
        tool.execute({"sources": ["jd_products", "tmall_products"]})
        assert reg.count >= 1

    def test_product_count_metric(self):
        reg = ClaimsRegistry()
        tool = CrossSourceComparisonTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"metric": "product_count"})
        assert result.error is None
        assert result.value["comparison"]["jd_products"]["count"] > 0

    def test_unknown_source_returns_empty(self):
        tool = CrossSourceComparisonTool(
            data_root=DATA_ROOT,
            registry=ClaimsRegistry(),
        )
        result = tool.execute({"sources": ["unknown_source"]})
        assert result.error is None
        assert result.value["comparison"]["unknown_source"]["count"] == 0

    def test_tool_protocol(self):
        tool = CrossSourceComparisonTool(
            data_root=DATA_ROOT,
            registry=ClaimsRegistry(),
        )
        assert tool.name == "compare_sources"
        assert "data:read" in tool.capabilities
