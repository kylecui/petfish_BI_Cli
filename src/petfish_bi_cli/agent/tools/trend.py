from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry
from petfish_bi_cli.ingestion.crocs import parse_crocs_csv
from petfish_bi_cli.sentiment.lexicon import analyze_batch_lexicon


@dataclass
class TrendTool:
    data_root: Path
    registry: ClaimsRegistry
    sources: Any = None
    name: str = "analyze_trend"
    description: str = "Analyze comment/price trends over time (daily/weekly/monthly buckets)"
    input_schema: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "bucket": {"type": "string", "enum": ["day", "week", "month"], "default": "day"},
                "metric": {"type": "string", "default": "comment_count"},
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
        bucket = args.get("bucket", "day")

        try:
            csv_path = None
            if self.sources is not None:
                csv_path = self.sources.resolve_path("crocs_xiaohongshu")
            if csv_path is None:
                import glob

                csv_files = glob.glob(str(self.data_root / "CROCS_*.csv"))
                csv_path = Path(csv_files[0]) if csv_files else None
            if csv_path is None:
                return ToolResult(error="No CROCS CSV data found")
            records = parse_crocs_csv(csv_path)
        except Exception as exc:
            return ToolResult(error=f"Failed to load data: {exc}")

        buckets: dict[str, list[Any]] = defaultdict(list)
        for r in records:
            bucket_key = self._bucket_key(r.comment_time, bucket)
            if bucket_key:
                buckets[bucket_key].append(r)

        if not buckets:
            return ToolResult(error="No valid timestamps found")

        trend_data: list[dict] = []
        for bucket_key in sorted(buckets.keys()):
            records_in_bucket = buckets[bucket_key]
            count = len(records_in_bucket)

            sentiments = analyze_batch_lexicon(
                [r.comment_text for r in records_in_bucket if r.comment_text]
            )
            pos_ratio = (
                sum(1 for s in sentiments if s.sentiment == "positive") / len(sentiments)
                if sentiments
                else 0.0
            )

            trend_data.append(
                {
                    "bucket": bucket_key,
                    "comment_count": count,
                    "positive_ratio": round(pos_ratio, 3),
                }
            )

        import uuid

        claim = Claim(
            id=f"c{uuid.uuid4().hex[:6]}",
            metric="trend_peak_bucket",
            value=float(max(trend_data, key=lambda x: x["comment_count"])["comment_count"]),
            source=source,
        )
        self.registry.add(claim)

        return ToolResult(
            value={
                "trend": trend_data,
                "bucket_type": bucket,
                "total_buckets": len(trend_data),
                "claims": [{"id": claim.id, "metric": claim.metric, "value": claim.value}],
            }
        )

    def _bucket_key(self, time_str: str, bucket: str) -> str | None:
        if not time_str:
            return None
        try:
            dt = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(time_str.strip(), "%Y-%m-%d")
            except ValueError:
                return None

        if bucket == "day":
            return dt.strftime("%Y-%m-%d")
        elif bucket == "week":
            iso = dt.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        elif bucket == "month":
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y-%m-%d")
