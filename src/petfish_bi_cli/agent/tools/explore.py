from __future__ import annotations

from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.semantic import load_all_metadata


class ExploreDataSourcesTool:
    """Tool for exploring available data sources and their schemas."""

    name = "explore_data_sources"
    description = (
        "Explore available BI data sources. Returns source IDs, descriptions, "
        "available metrics, and example questions. Call this first to understand "
        "what data you can query."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "source_id": {
                "type": "string",
                "description": "Optional: get details for a specific source. Omit for all sources.",
            }
        },
    }
    risk_level = RiskLevel.LOW
    capabilities = ("data:read",)
    side_effect = False
    idempotent = True
    external_egress = False
    requires_credentials = False
    credential_name: str | None = None

    def __init__(self, semantic_dir: Path):
        self._semantic_dir = semantic_dir

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source_id = args.get("source_id")
        all_meta = load_all_metadata(self._semantic_dir)

        if source_id:
            meta = all_meta.get(source_id)
            if meta is None:
                return ToolResult(error=f"Unknown source: {source_id}")
            return ToolResult(value=_meta_to_summary(meta))

        summaries = [_meta_to_summary(meta) for meta in all_meta.values()]
        return ToolResult(value={"sources": summaries, "count": len(summaries)})


def _meta_to_summary(meta) -> dict:
    return {
        "source_id": meta.source_id,
        "type": meta.source_type,
        "description": meta.description,
        "metrics": [m["name"] for m in meta.metrics],
        "example_questions": list(meta.example_questions),
    }
