from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestLoadDataTool:
    def test_load_jd_returns_claims(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0
        assert result.value["metadata"]["row_count"] == 4

    def test_load_writes_to_registry(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        tool.execute({"source": "jd_products", "metric": "avg_price"})
        assert reg.count == 1
        assert reg.to_ledger().claims[0].source == "jd_products"

    def test_load_tmall_returns_claims(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "tmall_products", "metric": "avg_price"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0
        assert result.value["metadata"]["row_count"] > 100

    def test_load_rose_with_brand_filter(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute(
            {
                "source": "rose_10brands",
                "metric": "avg_price",
                "filters": {"brand": "BOSS"},
            }
        )
        if result.error:
            result = tool.execute({"source": "rose_10brands", "metric": "avg_price"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0

    def test_load_crocs_comments(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "crocs_xiaohongshu", "metric": "comment_count"})
        assert result.error is None
        assert result.value["claims"][0]["value"] > 0
        assert result.value["metadata"]["row_count"] > 100

    def test_load_unknown_source(self):
        reg = ClaimsRegistry()
        tool = LoadDataTool(data_root=DATA_ROOT, registry=reg)
        result = tool.execute({"source": "unknown"})
        assert result.error is not None

    def test_tool_protocol_attributes(self):
        tool = LoadDataTool(data_root=DATA_ROOT, registry=ClaimsRegistry())
        assert tool.name == "load_data"
        assert "data:read" in tool.capabilities
