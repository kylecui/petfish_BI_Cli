from __future__ import annotations

from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.config.source_registry import SourceRegistry


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

    def __init__(
        self,
        sources: SourceRegistry | None = None,
        semantic_dir: Path | None = None,
    ):
        if sources is None:
            resolved = semantic_dir or Path("references/semantic")
            sources = SourceRegistry(config={}, semantic_dir=resolved)
        self._sources = sources

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source_id = args.get("source_id")
        all_sources = self._sources.all_sources()

        if source_id:
            decl = all_sources.get(source_id)
            if decl is None:
                return ToolResult(error=f"Unknown source: {source_id}")
            return ToolResult(value=_decl_to_summary(decl))

        summaries = [_decl_to_summary(decl) for decl in all_sources.values()]
        return ToolResult(value={"sources": summaries, "count": len(summaries)})


def _decl_to_summary(decl) -> dict:
    return {
        "source_id": decl.source_id,
        "type": decl.type,
        "description": decl.description,
        "metrics": [m.name for m in decl.metrics],
        "example_questions": list(decl.example_questions),
    }
