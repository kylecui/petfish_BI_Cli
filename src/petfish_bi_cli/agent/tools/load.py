from __future__ import annotations

import glob
import uuid
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry
from petfish_bi_cli.ingestion.crocs import parse_crocs_csv
from petfish_bi_cli.ingestion.jd import ProductRecord
from petfish_bi_cli.ingestion.tmall import parse_rose_jsonl, parse_tmall_jsonl

_SOURCE_ALIASES = {
    "crocs": "crocs_xiaohongshu",
    "xiaohongshu": "crocs_xiaohongshu",
    "小红书": "crocs_xiaohongshu",
    "jd": "jd_products",
    "京东": "jd_products",
    "tmall": "tmall_products",
    "天猫": "tmall_products",
    "rose": "rose_10brands",
}

_SOURCE_FILES = {
    "jd_products": "JD_CROCS_Raw_Memory_Dump.json",
    "tmall_products": "TMALL_CROCS_Raw_Memory_Dump.json",
    "rose_10brands": "ROSE_10BRANDS_Raw_Dump.json",
}


class LoadDataTool:
    """Tool for loading data from a BI source. Returns claims with IDs."""

    name = "load_data"
    description = (
        "Load data from a BI source. Returns claims with IDs — cite these IDs in your output. "
        "Args: source (jd_products, tmall_products, crocs_xiaohongshu, rose_10brands), "
        "metric (avg_price, comment_count, etc.), filters (optional)."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "metric": {"type": "string"},
            "filters": {"type": "object"},
        },
        "required": ["source"],
    }
    risk_level = RiskLevel.LOW
    capabilities = ("data:read",)
    side_effect = False
    idempotent = True
    external_egress = False
    requires_credentials = False
    credential_name: str | None = None

    def __init__(self, data_root: Path, registry: ClaimsRegistry):
        self._data_root = data_root
        self._registry = registry

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source = args.get("source", "")
        source = _SOURCE_ALIASES.get(source, source)
        if not source:
            return ToolResult(
                value={"error": "Missing 'source' parameter"},
                error=(
                    "Missing 'source'. "
                    "Use explore_data_sources to see available sources."
                ),
            )
        metric = args.get("metric", "avg_price")

        if source == "crocs_xiaohongshu":
            return self._load_crocs(metric, args.get("filters"))
        elif source == "jd_products":
            return self._load_products(source, metric, args.get("filters"), _parse_jd)
        elif source == "tmall_products":
            return self._load_products(source, metric, args.get("filters"), _parse_tmall)
        elif source == "rose_10brands":
            return self._load_products(source, metric, args.get("filters"), _parse_rose)
        else:
            return ToolResult(error=f"Unknown source: {source}")

    def _load_crocs(self, metric: str, filters: dict | None) -> ToolResult:
        csv_files = glob.glob(str(self._data_root / "CROCS_*.csv"))
        if not csv_files:
            return ToolResult(error="No CROCS CSV file found")
        records = parse_crocs_csv(Path(csv_files[0]))

        if metric in ("comment_count", "评论数"):
            count = len(records)
            claim = _make_claim(
                metric,
                float(count),
                "crocs_xiaohongshu",
                f"COUNT(评论内容 WHERE != '无') = {count}",
            )
        else:
            claim = _make_claim(
                metric, float(len(records)), "crocs_xiaohongshu", f"COUNT = {len(records)}"
            )

        self._registry.add(claim)
        self._registry.add_allowed_number(float(len(records)))
        return ToolResult(
            value={
                "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
                "metadata": {"source": "crocs_xiaohongshu", "row_count": len(records)},
            }
        )

    def _load_products(self, source: str, metric: str, filters: dict | None, parser) -> ToolResult:
        filename = _SOURCE_FILES.get(source)
        if not filename:
            return ToolResult(error=f"No file mapping for {source}")
        file_path = self._data_root / filename
        if not file_path.exists():
            return ToolResult(error=f"File not found: {filename}")

        records = parser(file_path)
        if filters and "brand" in filters:
            brand = filters["brand"].lower()
            records = [r for r in records if brand in r.title.lower() or brand in r.brand.lower()]

        prices = [r.price for r in records if r.price > 0]
        if not prices:
            return ToolResult(error=f"No valid price data in {source}")

        if metric in ("avg_price", "avg", "均价"):
            value = sum(prices) / len(prices)
            comp = f"AVG(price) over {len(prices)} items"
        elif metric in ("min_price", "min"):
            value = min(prices)
            comp = f"MIN(price) over {len(prices)} items"
        elif metric in ("max_price", "max"):
            value = max(prices)
            comp = f"MAX(price) over {len(prices)} items"
        elif metric in ("count", "product_count"):
            value = float(len(records))
            comp = f"COUNT = {len(records)}"
        else:
            value = sum(prices) / len(prices)
            comp = f"AVG(price) = {value}"

        claim = _make_claim(metric, round(value, 2), source, comp)
        self._registry.add(claim)
        self._registry.add_allowed_number(float(len(records)))
        self._registry.add_allowed_number(float(len(prices)))
        return ToolResult(
            value={
                "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
                "metadata": {"source": source, "row_count": len(records)},
            }
        )


def _make_claim(metric: str, value: float, source: str, computation: str) -> Claim:
    return Claim(
        id=f"c{uuid.uuid4().hex[:8]}",
        metric=metric,
        value=value,
        source=source,
        computation=computation,
    )


def _parse_jd(path: Path) -> list[ProductRecord]:
    from petfish_bi_cli.ingestion.jd import parse_jd_json

    return parse_jd_json(path)


def _parse_tmall(path: Path) -> list[ProductRecord]:
    return parse_tmall_jsonl(path)


def _parse_rose(path: Path) -> list[ProductRecord]:
    return parse_rose_jsonl(path)
