from __future__ import annotations

from pathlib import Path
from typing import Any

from petfishframework.core.contracts import Tool, ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry
from petfish_bi_cli.ingestion.timepoint import (
    TimepointSnapshot,
    list_timepoints,
    parse_rose_timepoints,
    parse_tmall_timepoints,
)


class CrossTimeTool(Tool):
    """Compare prices across time snapshots for TMALL/ROSE data."""

    def __init__(self, data_root: Path, registry: ClaimsRegistry):
        self.data_root = data_root
        self.registry = registry
        self._claim_counter = 0

    name = "cross_time_compare"
    description = (
        "Compare prices across different crawl timepoints. Use for trend-over-time analysis."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "tmall_products or rose_10brands"},
            "metric": {"type": "string", "description": "avg_price (default)"},
        },
    }
    risk_level = "low"
    capabilities = frozenset({"fs:read"})

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source = args.get("source", "tmall_products")
        if source not in ("tmall_products", "rose_10brands"):
            return ToolResult(value={"error": f"Unsupported source: {source}"}, error=True)

        snapshots = self._load_snapshots(source)
        if len(snapshots) < 2:
            available = list_timepoints(source, self.data_root)
            return ToolResult(
                value={
                    "error": "Need at least 2 timepoints for comparison",
                    "available_timepoints": available,
                    "count": len(snapshots),
                },
                error=True,
            )

        first = snapshots[0]
        last = snapshots[-1]
        comparisons = []
        for snap in snapshots:
            claim = self._make_claim(
                metric=f"avg_price_{source}_{snap.timestamp}",
                value=snap.avg_price,
                source=source,
                computation=f"avg of {snap.count} items at {snap.timestamp}",
            )
            comparisons.append(
                {
                    "timestamp": snap.timestamp,
                    "item_count": snap.count,
                    "avg_price": snap.avg_price,
                    "price_range": list(snap.price_range),
                    "claim_id": claim.id,
                }
            )

        diff = round(last.avg_price - first.avg_price, 2)
        pct = (
            round(abs(diff) / min(first.avg_price, last.avg_price) * 100, 1)
            if min(first.avg_price, last.avg_price) > 0
            else 0.0
        )
        diff_claim = self._make_claim(
            metric=f"price_change_{source}",
            value=diff,
            source="cross_time",
            computation=f"{last.avg_price} - {first.avg_price} = {diff}, pct={pct}%",
        )

        return ToolResult(
            value={
                "source": source,
                "timepoint_count": len(snapshots),
                "comparisons": comparisons,
                "trend": {
                    "first_avg": first.avg_price,
                    "last_avg": last.avg_price,
                    "change": diff,
                    "change_pct": pct,
                    "direction": "up" if diff > 0 else "down" if diff < 0 else "stable",
                    "claim_id": diff_claim.id,
                },
                "claims": [
                    {
                        "id": c["claim_id"],
                        "metric": c["metric"] if "metric" in c else "",
                        "value": c["avg_price"],
                    }
                    for c in comparisons
                ],
            }
        )

    def _load_snapshots(self, source: str) -> list[TimepointSnapshot]:
        if source == "tmall_products":
            path = self.data_root / "TMALL_CROCS_Raw_Memory_Dump.json"
            return parse_tmall_timepoints(path)
        path = self.data_root / "ROSE_10BRANDS_Raw_Dump.json"
        return parse_rose_timepoints(path)

    def _make_claim(self, metric: str, value: float, source: str, computation: str = "") -> Claim:
        self._claim_counter += 1
        claim = Claim(
            id=f"ct{self._claim_counter}",
            metric=metric,
            value=value,
            source=source,
            computation=computation,
        )
        self.registry.add(claim)
        return claim
