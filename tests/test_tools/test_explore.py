from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool

SEMANTIC_DIR = Path(__file__).parent.parent.parent / "references" / "semantic"


class TestExploreDataSourcesTool:
    def test_explore_all_returns_four_sources(self):
        tool = ExploreDataSourcesTool(semantic_dir=SEMANTIC_DIR)
        result = tool.execute({})
        assert result.error is None
        data = result.value
        assert data["count"] == 4
        source_ids = [s["source_id"] for s in data["sources"]]
        assert "jd_products" in source_ids
        assert "tmall_products" in source_ids

    def test_explore_specific_source(self):
        tool = ExploreDataSourcesTool(semantic_dir=SEMANTIC_DIR)
        result = tool.execute({"source_id": "jd_products"})
        assert result.error is None
        assert result.value["source_id"] == "jd_products"
        assert "avg_price" in result.value["metrics"]

    def test_explore_unknown_source(self):
        tool = ExploreDataSourcesTool(semantic_dir=SEMANTIC_DIR)
        result = tool.execute({"source_id": "nonexistent"})
        assert result.error is not None

    def test_tool_protocol_attributes(self):
        tool = ExploreDataSourcesTool(semantic_dir=SEMANTIC_DIR)
        assert tool.name == "explore_data_sources"
        assert tool.description
        assert tool.input_schema
        assert tool.risk_level is not None
        assert "data:read" in tool.capabilities
