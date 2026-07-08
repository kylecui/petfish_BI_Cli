from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry
from petfish_bi_cli.ingestion.crocs import parse_crocs_csv
from petfish_bi_cli.sentiment.lexicon import (
    aggregate_sentiments,
    analyze_batch_lexicon,
)
from petfish_bi_cli.sentiment.llm_batch import LLMSentimentBatch


@dataclass
class SentimentAnalysisTool:
    data_root: Path
    registry: ClaimsRegistry
    model: Any = None
    mode: str = "hybrid"
    batch_size: int = 50
    name: str = "analyze_sentiment"
    description: str = (
        "Analyze sentiment of e-commerce comments (positive/negative/neutral, topics, pain points)"
    )
    input_schema: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Data source ID (e.g. crocs_xiaohongshu)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["hybrid", "llm", "lexicon"],
                    "default": "hybrid",
                },
            },
            "required": ["source"],
        }
    )
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ("data:read",)
    side_effect: bool = False
    idempotent: bool = True
    external_egress: bool = False
    requires_credentials: bool = False
    credential_name: str | None = None

    def execute(self, args: dict[str, Any]) -> ToolResult:
        source = args.get("source", "crocs_xiaohongshu")
        mode = args.get("mode", self.mode)

        try:
            comments = self._load_comments(source)
        except Exception as exc:
            return ToolResult(error=f"Failed to load comments: {exc}")

        if not comments:
            return ToolResult(error=f"No comments found in {source}")

        if mode == "lexicon":
            results = analyze_batch_lexicon(comments)
        elif mode == "llm" and self.model is not None:
            batch = LLMSentimentBatch(model=self.model, batch_size=self.batch_size)
            results = batch.analyze(comments)
        elif mode == "hybrid":
            results = analyze_batch_lexicon(comments)
            uncertain = [r for r in results if r.sentiment == "neutral"]
            if uncertain and self.model is not None:
                uncertain_texts = [r.text for r in uncertain]
                batch = LLMSentimentBatch(model=self.model, batch_size=self.batch_size)
                llm_results = batch.analyze(uncertain_texts)
                llm_map = {r.text: r for r in llm_results}
                results = [
                    llm_map.get(r.text, r) if r.sentiment == "neutral" else r for r in results
                ]
        else:
            results = analyze_batch_lexicon(comments)

        agg = aggregate_sentiments(results)

        claims: list[Claim] = [
            Claim(
                id=f"c{uuid.uuid4().hex[:6]}",
                metric="sentiment_positive_ratio",
                value=agg["positive"],
                source=source,
            ),
            Claim(
                id=f"c{uuid.uuid4().hex[:6]}",
                metric="sentiment_negative_ratio",
                value=agg["negative"],
                source=source,
            ),
            Claim(
                id=f"c{uuid.uuid4().hex[:6]}",
                metric="sentiment_neutral_ratio",
                value=agg["neutral"],
                source=source,
            ),
            Claim(
                id=f"c{uuid.uuid4().hex[:6]}",
                metric="comment_count",
                value=float(agg["total"]),
                source=source,
            ),
        ]

        for claim in claims:
            self.registry.add(claim)

        top_topics = agg.get("top_topics", [])

        return ToolResult(
            value={
                "sentiment_distribution": {
                    "positive": agg["positive"],
                    "negative": agg["negative"],
                    "neutral": agg["neutral"],
                },
                "comment_count": agg["total"],
                "top_topics": top_topics,
                "claims": [{"id": c.id, "metric": c.metric, "value": c.value} for c in claims],
            }
        )

    def _load_comments(self, source: str) -> list[str]:
        if source == "crocs_xiaohongshu":
            csv_path = self.data_root / "CROCS_原始数据_20260605_144849.csv"
            records = parse_crocs_csv(csv_path)
            return [r.comment_text for r in records if r.comment_text]
        return []
