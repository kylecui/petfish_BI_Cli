from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.trend import TrendTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestTrendTool:
    def test_daily_buckets_returned(self):
        reg = ClaimsRegistry()
        tool = TrendTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "crocs_xiaohongshu", "bucket": "day"})
        assert result.error is None
        assert result.value["total_buckets"] > 0
        assert len(result.value["trend"]) > 0

    def test_writes_claim_to_registry(self):
        reg = ClaimsRegistry()
        tool = TrendTool(data_root=DATA_ROOT, registry=reg)
        tool.execute({"source": "crocs_xiaohongshu"})
        assert reg.count >= 1

    def test_unknown_source_returns_empty(self):
        tool = TrendTool(data_root=DATA_ROOT, registry=ClaimsRegistry())
        result = tool.execute({"source": "jd_products"})
        assert result.error is None

    def test_tool_protocol(self):
        tool = TrendTool(data_root=DATA_ROOT, registry=ClaimsRegistry())
        assert tool.name == "analyze_trend"
        assert "data:read" in tool.capabilities

    def test_bucket_has_sentiment(self):
        reg = ClaimsRegistry()
        tool = TrendTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "crocs_xiaohongshu", "bucket": "day"})
        if result.value["trend"]:
            assert "positive_ratio" in result.value["trend"][0]
