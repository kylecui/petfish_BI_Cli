from __future__ import annotations

import glob
import uuid
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.config.source_registry import MetricSpec, SourceDeclaration, SourceRegistry
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

_KNOWN_FILE_PATTERNS = {
    "jd_products": "JD_CROCS_Raw_Memory_Dump.json",
    "tmall_products": "TMALL_CROCS_Raw_Memory_Dump.json",
    "rose_10brands": "ROSE_10BRANDS_Raw_Dump.json",
}

_MOCK_FILE_PATTERNS = {
    "jd_products": "mock_jd_products.json",
    "tmall_products": "mock_tmall_products.json",
    "rose_10brands": "mock_rose_10brands.json",
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

    def __init__(
        self,
        sources: SourceRegistry | None = None,
        registry: ClaimsRegistry | None = None,
        data_root: Path | None = None,
        semantic_dir: Path | None = None,
    ):
        if sources is None:
            resolved_root = data_root or Path("references")
            sources = SourceRegistry(
                config={},
                data_root=resolved_root,
                semantic_dir=semantic_dir or resolved_root / "semantic",
            )
        self._sources = sources
        self._registry = registry or ClaimsRegistry()
        self._data_root = data_root or Path("references")

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source_input = args.get("source", "")
        source_id = _SOURCE_ALIASES.get(source_input, source_input)
        if not source_id:
            return ToolResult(
                value={"error": "Missing 'source' parameter"},
                error="Missing 'source'. Use explore_data_sources to see available sources.",
            )

        decl = self._sources.get(source_id)
        if decl is None:
            return ToolResult(error=f"Unknown source: {source_id}")

        metric_input = args.get("metric", "avg_price")

        if source_id == "crocs_xiaohongshu":
            return self._load_crocs(metric_input, args.get("filters"))

        records = self._load_product_records(decl, source_id)
        if records is None:
            return ToolResult(error=f"Could not load data for source: {source_id}")

        filters = args.get("filters")
        if filters and "brand" in filters:
            brand = filters["brand"].lower()
            records = [r for r in records if brand in r.title.lower() or brand in r.brand.lower()]

        prices = [r.price for r in records if r.price > 0]
        if not prices and metric_input not in ("count", "product_count"):
            return ToolResult(error=f"No valid price data in {source_id}")

        value, comp = self._compute_metric(records, prices, metric_input, decl)

        claim = _make_claim(metric_input, round(value, 2), source_id, comp)
        self._registry.add(claim)
        self._registry.add_allowed_number(float(len(records)))
        if prices:
            self._registry.add_allowed_number(float(len(prices)))

        return ToolResult(
            value={
                "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
                "metadata": {"source": source_id, "row_count": len(records)},
            }
        )

    def _load_crocs(self, metric: str, filters: dict | None) -> ToolResult:
        csv_files = glob.glob(str(self._data_root / "CROCS_*.csv"))
        if not csv_files:
            mock_path = self._data_root / "mock_crocs_xiaohongshu.csv"
            if mock_path.exists():
                csv_files = [str(mock_path)]
        if not csv_files:
            return ToolResult(error="No CROCS CSV file found")
        records = parse_crocs_csv(Path(csv_files[0]))

        count = len(records)
        if metric in ("comment_count", "评论数"):
            comp = f"COUNT(评论内容 WHERE != '无') = {count}"
        else:
            comp = f"COUNT = {count}"

        claim = _make_claim(metric, float(count), "crocs_xiaohongshu", comp)
        self._registry.add(claim)
        self._registry.add_allowed_number(float(count))
        return ToolResult(
            value={
                "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
                "metadata": {"source": "crocs_xiaohongshu", "row_count": count},
            }
        )

    def _load_product_records(
        self, decl: SourceDeclaration, source_id: str,
    ) -> list[ProductRecord] | None:
        file_path = self._resolve_file(decl, source_id)
        if file_path is None or not file_path.exists():
            return None

        if source_id == "jd_products":
            from petfish_bi_cli.ingestion.jd import parse_jd_json

            return parse_jd_json(file_path)
        if source_id == "tmall_products":
            return parse_tmall_jsonl(file_path)
        if source_id == "rose_10brands":
            return parse_rose_jsonl(file_path)
        return None

    def _resolve_file(self, decl: SourceDeclaration, source_id: str) -> Path | None:
        if decl.path and decl.path.exists():
            return decl.path
        pattern = decl.file_pattern or _KNOWN_FILE_PATTERNS.get(source_id, "")
        if pattern:
            candidate = self._data_root / pattern
            if candidate.exists():
                return candidate
        mock_pattern = _MOCK_FILE_PATTERNS.get(source_id, "")
        if mock_pattern:
            candidate = self._data_root / mock_pattern
            if candidate.exists():
                return candidate
        return None

    def _compute_metric(
        self,
        records: list[ProductRecord],
        prices: list[float],
        metric_input: str,
        decl: SourceDeclaration,
    ) -> tuple[float, str]:
        spec = _find_metric_spec(decl, metric_input)

        if spec is not None:
            agg = spec.aggregation.lower()
            if agg == "count":
                return float(len(records)), f"COUNT = {len(records)}"
            if prices:
                if agg == "avg":
                    return sum(prices) / len(prices), f"AVG(price) over {len(prices)} items"
                if agg == "min":
                    return min(prices), f"MIN(price) over {len(prices)} items"
                if agg == "max":
                    return max(prices), f"MAX(price) over {len(prices)} items"
                if agg == "sum":
                    return sum(prices), f"SUM(price) over {len(prices)} items"

        if metric_input in ("avg_price", "avg", "均价") and prices:
            return sum(prices) / len(prices), f"AVG(price) over {len(prices)} items"
        if metric_input in ("min_price", "min") and prices:
            return min(prices), f"MIN(price) over {len(prices)} items"
        if metric_input in ("max_price", "max") and prices:
            return max(prices), f"MAX(price) over {len(prices)} items"
        if metric_input in ("count", "product_count"):
            return float(len(records)), f"COUNT = {len(records)}"

        if prices:
            return sum(prices) / len(prices), f"AVG(price) = {sum(prices) / len(prices)}"
        return 0.0, "No data"


def _find_metric_spec(decl: SourceDeclaration, metric_input: str) -> MetricSpec | None:
    for m in decl.metrics:
        if m.name == metric_input or metric_input in m.aliases:
            return m
    return None


def _make_claim(metric: str, value: float, source: str, computation: str) -> Claim:
    return Claim(
        id=f"c{uuid.uuid4().hex[:8]}",
        metric=metric,
        value=value,
        source=source,
        computation=computation,
    )
