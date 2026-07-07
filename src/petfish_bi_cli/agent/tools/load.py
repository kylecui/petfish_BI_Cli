from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry


class LoadDataTool:
    """Tool for loading data from a source. Returns ClaimsLedger (metadata, not raw data).

    M-1 stub: returns hardcoded fixture claims. M1 will replace with real ingestion.
    """

    name = "load_data"
    description = (
        "Load data from a BI source. Returns claims with IDs — cite these IDs in your output. "
        "Args: source (one of: jd_products, tmall_products, crocs_xiaohongshu, rose_10brands), "
        "metric (e.g. avg_price, comment_count), filters (optional dict)."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Data source ID"},
            "metric": {"type": "string", "description": "Metric to compute"},
            "filters": {"type": "object", "description": "Optional filters (e.g. {brand: CROCS})"},
        },
        "required": ["source"],
    }
    risk_level = RiskLevel.LOW
    capabilities = ("fs:read",)

    _FIXTURES: dict = {
        "jd_products": [
            {
                "skuName": "CROCS 云朵经典洞洞鞋",
                "calculatedFinalPrice": 489.0,
                "shopName": "CROCS京东自营",
            },
            {
                "skuName": "CROCS 经典款",
                "calculatedFinalPrice": 359.0,
                "shopName": "CROCS京东自营",
            },
        ],
        "tmall_products": [
            {"title": "Crocs洞洞鞋", "price": "407.01", "shop": "银泰百货旗舰店"},
        ],
    }

    def __init__(self, data_root: Path, registry: ClaimsRegistry):
        self._data_root = data_root
        self._registry = registry

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source = args["source"]
        metric = args.get("metric", "avg_price")

        fixture = self._FIXTURES.get(source)
        if fixture is None:
            return ToolResult(error=f"Unknown source: {source}. Use explore_data_sources first.")

        if source == "jd_products":
            prices = [r["calculatedFinalPrice"] for r in fixture]
            avg = sum(prices) / len(prices)
            claim = Claim(
                id=f"c{uuid.uuid4().hex[:8]}",
                metric=metric,
                value=round(avg, 2),
                source=source,
                source_rows=tuple(r["skuName"] for r in fixture),
                computation=f"AVG(calculatedFinalPrice) = {avg}",
            )
        elif source == "tmall_products":
            prices = [float(r["price"]) for r in fixture]
            avg = sum(prices) / len(prices) if prices else 0
            claim = Claim(
                id=f"c{uuid.uuid4().hex[:8]}",
                metric=metric,
                value=round(avg, 2),
                source=source,
                source_rows=tuple(r["shop"] for r in fixture),
                computation=f"AVG(price) = {avg}",
            )
        else:
            return ToolResult(error=f"Stub does not support source: {source}")

        self._registry.add(claim)
        return ToolResult(value={
            "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
            "metadata": {"source": source, "row_count": len(fixture)},
        })
