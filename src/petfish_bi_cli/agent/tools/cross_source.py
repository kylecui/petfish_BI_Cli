from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry
from petfish_bi_cli.ingestion.jd import parse_jd_json
from petfish_bi_cli.ingestion.rose import parse_rose_jsonl
from petfish_bi_cli.ingestion.tmall import parse_tmall_jsonl

_CROSS_SOURCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Data source IDs to compare",
        },
        "metric": {"type": "string", "default": "avg_price"},
    },
    "required": ["sources"],
}


@dataclass
class CrossSourceComparisonTool:
    data_root: Path
    registry: ClaimsRegistry
    _claim_counter: int = field(default=0, repr=False)

    name: str = "compare_sources"
    description: str = "Compare metrics across data sources (e.g. JD vs TMALL price comparison)"
    input_schema: dict[str, Any] = field(default_factory=lambda: _CROSS_SOURCE_SCHEMA)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ("data:read",)

    def execute(self, args: dict[str, Any]) -> ToolResult:
        sources = args.get("sources", ["jd_products", "tmall_products"])

        stats: dict[str, dict[str, float]] = {}
        for source in sources:
            try:
                prices = self._load_prices(source)
                if prices:
                    stats[source] = {
                        "count": float(len(prices)),
                        "avg": round(sum(prices) / len(prices), 2),
                        "min": min(prices),
                        "max": max(prices),
                        "range": round(max(prices) - min(prices), 2),
                    }
                else:
                    stats[source] = {"count": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0, "range": 0.0}
            except Exception:
                stats[source] = {"count": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0, "range": 0.0}

        claims_out: list[dict] = []
        if len(sources) >= 2 and all(stats[s]["avg"] > 0 for s in sources[:2]):
            s1, s2 = sources[0], sources[1]
            diff = round(stats[s1]["avg"] - stats[s2]["avg"], 2)
            pct = (
                round(abs(diff) / min(stats[s1]["avg"], stats[s2]["avg"]) * 100, 1)
                if min(stats[s1]["avg"], stats[s2]["avg"]) > 0
                else 0.0
            )

            claim = self._make_claim(
                metric=f"price_diff_{s1}_vs_{s2}",
                value=diff,
                source="cross_source",
                computation=(
                    f"compare({stats[s1]['avg']} - {stats[s2]['avg']}) = {diff}, pct={pct}%"
                ),
            )
            claims_out.append({"id": claim.id, "metric": claim.metric, "value": claim.value})

            return ToolResult(
                value={
                    "comparison": stats,
                    "difference": {
                        "absolute": diff,
                        "percentage": pct,
                        "higher": s1 if diff > 0 else s2,
                    },
                    "claims": claims_out,
                }
            )

        return ToolResult(
            value={
                "comparison": stats,
                "claims": claims_out,
            }
        )

    def _make_claim(
        self, metric: str, value: float | str, source: str, computation: str = ""
    ) -> Claim:
        self._claim_counter += 1
        claim = Claim(
            id=f"cs{self._claim_counter}",
            metric=metric,
            value=value,
            source=source,
            computation=computation,
        )
        self.registry.add(claim)
        return claim

    def _load_prices(self, source: str) -> list[float]:
        if source == "jd_products":
            path = self.data_root / "JD_CROCS_Raw_Memory_Dump.json"
            products = parse_jd_json(path)
            return [p.price for p in products if p.price > 0]
        elif source == "tmall_products":
            path = self.data_root / "TMALL_CROCS_Raw_Memory_Dump.json"
            products = parse_tmall_jsonl(path)
            return [p.price for p in products if p.price > 0]
        elif source == "rose_10brands":
            path = self.data_root / "ROSE_10BRANDS_Raw_Dump.json"
            products = parse_rose_jsonl(path)
            return [p.price for p in products if p.price > 0]
        return []
