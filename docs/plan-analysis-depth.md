# Plan: Analysis Depth (M5)

> **Status**: Planning
> **Priority**: 🔴 High — delivers BI value (sentiment, trend, cross-source)
> **Depends on**: M4 (real model for LLM-based sentiment)
> **Estimated effort**: 3-4 sessions

## 1. Problem Statement

Current tools only return surface-level aggregates (count, avg, min, max). The richest data source — 2034 小红书 comments — is reduced to `comment_count`. Missing:

1. **Sentiment analysis**: Are comments positive or negative? What topics recur?
2. **Trend analysis**: How do comment volume / sentiment change over time?
3. **Cross-source comparison**: Beyond avg price diff, what about shop distribution, price ranges, product variety?
4. **Pain point extraction**: What specific complaints do users have (磨脚, 掉色, 开胶)?

## 2. Research Basis

| Source | Finding | Application |
|---|---|---|
| buluslan/review-analyzer-skill (⭐92) | 22-dimension Chinese e-commerce tag system | Custom lexicon design |
| CerealAxis/JRAS | Multi-strategy review analysis pipeline | Hybrid (lexicon + LLM) architecture |
| LLM batch sentiment (GPT-4o-mini) | ~$0.20 for 2000 comments, structured JSON output | Primary sentiment engine |
| jieba + custom lexicon | <1ms per comment, $0, ~60% coverage | Fast-path / offline fallback |
| SnowNLP | Maintained poorly, ~60-70% accuracy on e-commerce | ❌ Rejected — quality too low |

### Hybrid Architecture Decision

```
Comment → jieba lexicon match?
    ├── YES (60%) → instant classification (<1ms, $0)
    └── NO  (40%) → LLM batch (structured JSON, $0.20 total)
```

**Rationale**: 60% of comments contain obvious sentiment words (舒服/好看/磨脚/硬). Lexicon catches these instantly. The remaining 40% need contextual understanding (e.g., "本来觉得一般但穿了之后真香" → positive after initial hesitation). LLM handles nuance.

## 3. Tool Design

### 3.1 SentimentAnalysisTool

```python
class SentimentAnalysisTool:
    """Analyzes sentiment + topics + pain points in UGC comments.

    Hybrid mode: lexicon fast-path → LLM for misses.
    All results enter ClaimsLedger as grounded claims.
    """
    name = "analyze_sentiment"
    description = "Analyze sentiment, topics, and pain points in user comments"
    input_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Data source ID"},
            "mode": {"type": "string", "enum": ["hybrid", "llm", "lexicon"]},
            "sample_size": {"type": "integer", "description": "Max comments to process"},
        },
        "required": ["source"],
    }
```

**Output structure** (ToolResult.value):
```python
{
    "total_comments": 2034,
    "analyzed": 2034,
    "sentiment_distribution": {
        "positive": 0.62,    # 1261 comments
        "negative": 0.23,    # 468 comments
        "neutral": 0.15,     # 305 comments
    },
    "top_topics": [
        {"topic": "舒适度", "count": 520, "sentiment": 0.78},
        {"topic": "磨脚", "count": 312, "sentiment": 0.12},
        {"topic": "好看", "count": 280, "sentiment": 0.91},
    ],
    "pain_points": [
        {"point": "磨脚", "count": 187, "sample": "...后跟磨得厉害..."},
        {"point": "偏贵", "count": 95, "sample": "...性价比不高..."},
    ],
    "claims": [
        {"id": "c501", "metric": "positive_ratio", "value": 0.62, "source": "crocs_xiaohongshu"},
        {"id": "c502", "metric": "negative_ratio", "value": 0.23, "source": "crocs_xiaohongshu"},
        {"id": "c503", "metric": "pain_point_磨脚_count", "value": 187, "source": "crocs_xiaohongshu"},
    ],
}
```

### 3.2 TrendAnalysisTool

```python
class TrendAnalysisTool:
    """Time-bucket aggregation for time-series analysis."""
    name = "analyze_trend"
    input_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "metric": {"type": "string", "enum": ["comment_count", "avg_sentiment", "price"]},
            "bucket": {"type": "string", "enum": ["day", "week", "month"]},
        },
        "required": ["source", "metric", "bucket"],
    }
```

**Output**:
```python
{
    "buckets": [
        {"date": "2024-06-01", "value": 45, "count": 45},
        {"date": "2024-06-02", "value": 78, "count": 78},
        # ...
    ],
    "trend": "increasing",       # increasing | decreasing | stable
    "change_pct": 23.5,
    "claims": [
        {"id": "c601", "metric": "trend_direction", "value": 1.0, "source": "trend_analysis"},
        {"id": "c602", "metric": "trend_change_pct", "value": 23.5, "source": "trend_analysis"},
    ],
}
```

### 3.3 CrossSourceComparisonTool

```python
class CrossSourceComparisonTool:
    """Deep comparison across data sources (e.g., JD vs TMALL)."""
    name = "compare_sources"
    input_schema = {
        "type": "object",
        "properties": {
            "sources": {"type": "array", "items": {"type": "string"}},
            "dimensions": {
                "type": "array",
                "items": {"type": "string", "enum": ["price", "shop", "variety", "sentiment"]},
            },
        },
        "required": ["sources"],
    }
```

**Output**:
```python
{
    "comparison": {
        "jd_products": {"avg_price": 424.0, "shop_count": 2, "price_range": [299, 549]},
        "tmall_products": {"avg_price": 407.01, "shop_count": 87, "price_range": [89, 559]},
    },
    "differences": {
        "price_diff": 16.99,
        "price_diff_pct": 4.2,
        "shop_count_ratio": 43.5,     # TMALL has 43x more shops
    },
    "claims": [
        {"id": "c701", "metric": "jd_shop_count", "value": 2, "source": "jd_products"},
        {"id": "c702", "metric": "tmall_shop_count", "value": 87, "source": "tmall_products"},
        {"id": "c703", "metric": "shop_count_ratio", "value": 43.5, "source": "cross_source"},
    ],
}
```

## 4. Configuration Format

```yaml
# configs/bi_cli.yml — analysis section
analysis:
  sentiment:
    mode: hybrid                      # hybrid | llm | lexicon
    llm:
      model_role: primary             # reuse model.roles.primary
      batch_size: 50
      concurrency: 10                 # ThreadPoolExecutor workers
      prompt_template: configs/prompts/sentiment_analysis.md
    lexicon:
      custom_file: configs/crocs_lexicon.txt
      positive_words: [舒服, 好看, 百搭, 推荐, 值得, 真香, 绝绝子]
      negative_words: [磨脚, 硬, 臭, 掉色, 开胶, 退款, 踩雷, 踩坑]
      negation_words: [不, 没, 别, 莫]  # 否定前缀反转极性
    thresholds:
      positive: 0.6
      negative: 0.4

  trend:
    default_bucket: day               # day | week | month
    date_field_map:                   # per-source date column
      crocs_xiaohongshu: 评论时间
      tmall_products: _timestamp
      rose_10brands: _timestamp

  cross_source:
    default_sources: [jd_products, tmall_products]
    default_dimensions: [price, shop]
```

## 5. Code Structure

```
src/petfish_bi_cli/
├── sentiment/
│   ├── __init__.py
│   ├── lexicon.py                   # NEW: jieba + custom lexicon fast-path
│   ├── llm_batch.py                 # NEW: LLM batch sentiment for misses
│   └── types.py                     # NEW: SentimentResult, TopicResult, PainPoint
├── agent/tools/
│   ├── sentiment.py                 # NEW: SentimentAnalysisTool
│   ├── trend.py                     # NEW: TrendAnalysisTool
│   └── cross_source.py              # NEW: CrossSourceComparisonTool
└── ingestion/
    └── (existing adapters, no change)
```

### 5.1 lexicon.py (Fast-Path)

```python
from __future__ import annotations
import jieba
from dataclasses import dataclass

from .types import SentimentResult


@dataclass
class LexiconConfig:
    positive: set[str]
    negative: set[str]
    negation: set[str]


def classify_lexicon(text: str, config: LexiconConfig) -> SentimentResult | None:
    """Return SentimentResult if lexicon matches, None if no signal."""
    words = set(jieba.cut(text))
    pos_hits = words & config.positive
    neg_hits = words & config.negative

    # negation check: 不舒服 → negative, 不好看 → negative
    for neg_word in config.negation:
        for pos_word in list(pos_hits):
            if neg_word + pos_word in text:
                pos_hits.discard(pos_word)
                neg_hits.add(neg_word + pos_word)

    if not pos_hits and not neg_hits:
        return None  # no lexicon signal → defer to LLM

    score = (len(pos_hits) - len(neg_hits)) / max(len(pos_hits) + len(neg_hits), 1)
    label = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")

    return SentimentResult(
        sentiment=label,
        score=score,
        matched_words=tuple(pos_hits | neg_hits),
        method="lexicon",
    )
```

### 5.2 llm_batch.py (LLM Backfill)

```python
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .types import SentimentResult


def classify_llm_batch(
    comments: list[str],
    model_adapter: Any,
    prompt_template: str,
    batch_size: int = 50,
    concurrency: int = 10,
) -> list[SentimentResult]:
    """Batch-classify comments via LLM. Returns structured SentimentResults."""
    batches = [
        comments[i:i + batch_size]
        for i in range(0, len(comments), batch_size)
    ]

    def process_batch(batch: list[str]) -> list[dict]:
        prompt = prompt_template.replace("{COMMENTS}", json.dumps(batch, ensure_ascii=False))
        response = model_adapter.query_simple(prompt)
        return json.loads(response)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        all_results = list(pool.map(process_batch, batches))

    flat: list[dict] = [item for batch in all_results for item in batch]
    return [
        SentimentResult(
            sentiment=r["sentiment"],
            score=r.get("score", 0.5),
            topics=tuple(r.get("topics", [])),
            pain_points=tuple(r.get("pain_points", [])),
            method="llm",
        )
        for r in flat
    ]
```

### 5.3 sentiment tool

```python
from __future__ import annotations
from pathlib import Path

from petfishframework.core.contracts import Tool
from petfishframework.core.types import ToolResult
from petfish_bi_cli.grounding.claims import ClaimsRegistry, Claim
from petfish_bi_cli.sentiment.lexicon import classify_lexicon, LexiconConfig
from petfish_bi_cli.sentiment.llm_batch import classify_llm_batch


class SentimentAnalysisTool:
    def __init__(self, config: dict, registry: ClaimsRegistry, data_root: Path):
        self._config = config
        self._registry = registry
        self._data_root = data_root
        self._lexicon = _build_lexicon(config.get("lexicon", {}))

    name = "analyze_sentiment"
    description = "Analyze sentiment, topics, and pain points in user comments"
    input_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "mode": {"type": "string", "enum": ["hybrid", "llm", "lexicon"]},
        },
        "required": ["source"],
    }
    risk_level = "low"
    capabilities = ("compute:sentiment",)

    def execute(self, args: dict) -> ToolResult:
        source = args["source"]
        mode = args.get("mode", self._config.get("mode", "hybrid"))

        comments = self._load_comments(source)
        if not comments:
            return ToolResult(error=f"No comments found in {source}")

        results = []
        llm_misses = []

        for comment in comments:
            if mode in ("hybrid", "lexicon"):
                lex_result = classify_lexicon(comment, self._lexicon)
                if lex_result:
                    results.append(lex_result)
                    continue
            if mode in ("hybrid", "llm"):
                llm_misses.append(comment)

        if llm_misses and mode in ("hybrid", "llm"):
            llm_results = classify_llm_batch(
                llm_misses,
                model_adapter=self._get_model(),
                prompt_template=self._load_prompt(),
            )
            results.extend(llm_results)

        summary = self._summarize(results, source)
        return ToolResult(value=summary)

    def _summarize(self, results, source) -> dict:
        total = len(results)
        if total == 0:
            return {"total": 0, "claims": []}

        pos = sum(1 for r in results if r.sentiment == "positive")
        neg = sum(1 for r in results if r.sentiment == "negative")

        claims = []
        claims.append(self._registry.add(Claim(
            id="",
            metric="positive_ratio",
            value=pos / total,
            source=source,
        )))
        claims.append(self._registry.add(Claim(
            id="",
            metric="negative_ratio",
            value=neg / total,
            source=source,
        )))

        topic_counts: dict[str, int] = {}
        for r in results:
            for topic in r.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:5]:
            claims.append(self._registry.add(Claim(
                id="",
                metric=f"topic_{topic}_count",
                value=float(count),
                source=source,
            )))

        return {
            "total_comments": total,
            "sentiment_distribution": {
                "positive": pos / total,
                "negative": neg / total,
                "neutral": (total - pos - neg) / total,
            },
            "claims": [{"id": c.id, "metric": c.metric, "value": c.value} for c in claims],
        }
```

## 6. TDD Task Breakdown

| Task ID | Description | Test (RED) | Implementation (GREEN) |
|---|---|---|---|
| M5-T001 | Lexicon: positive match | `test_lexicon_舒服` → `sentiment == "positive"` | `lexicon.py: classify_lexicon()` |
| M5-T002 | Lexicon: negative match | `test_lexicon_磨脚` → `sentiment == "negative"` | Same |
| M5-T003 | Lexicon: negation flip | `test_lexicon_不舒服` → `sentiment == "negative"` | Negation logic |
| M5-T004 | Lexicon: no signal → None | `test_lexicon_不知道` → `result is None` | Same |
| M5-T005 | LLM batch: structured output | `test_llm_batch_3_comments` → 3 SentimentResults | `llm_batch.py: classify_llm_batch()` |
| M5-T006 | LLM batch: concurrent processing | `test_llm_batch_concurrency` → 100 comments, <5s | ThreadPoolExecutor |
| M5-T007 | Sentiment tool: hybrid mode | `test_sentiment_tool_hybrid` → mix of lexicon+llm results | `sentiment.py: execute()` |
| M5-T008 | Sentiment tool: returns claims | `test_sentiment_tool_claims` → claims in registry | ClaimsRegistry integration |
| M5-T009 | Sentiment tool: empty source error | `test_sentiment_tool_empty` → ToolResult(error=...) | Error handling |
| M5-T010 | Trend tool: daily buckets | `test_trend_daily` → grouped by day | `trend.py` |
| M5-T011 | Trend tool: trend direction | `test_trend_direction` → "increasing" | Direction calculation |
| M5-T012 | Cross-source: price comparison | `test_cross_source_price` → JD vs TMALL deep diff | `cross_source.py` |
| M5-T013 | Cross-source: shop distribution | `test_cross_source_shops` → shop_count per source | Same |
| M5-T014 | Integration: real CROCS data | `test_smoke_sentiment_real` → @integration, 2034 comments, assert pos > 0.3 | End-to-end |

## 7. Dependencies

No new Python dependencies required:

- `jieba 0.42.1` — already installed
- `snownlp 0.12.3` — already installed (not used, can remove)
- LLM sentiment reuses `model.roles.primary` from M4

## 8. ADR

### ADR-018: Hybrid Sentiment Architecture (Lexicon + LLM)

**Decision**: Sentiment analysis uses a two-tier hybrid approach. Tier 1 (jieba lexicon) handles ~60% of comments with obvious sentiment words in <1ms at $0 cost. Tier 2 (LLM batch) handles the remaining ~40% with contextual understanding at ~$0.20 for 2000 comments.

**Rationale**: Pure lexicon misses nuance ("本来觉得一般但穿了之后真香" → positive with context). Pure LLM is unnecessarily expensive for obvious cases ("磨脚" → negative, no context needed). Hybrid gets best of both.

**Alternatives considered**:
- LLM-only: $0.20/query × every query = expensive for repeated analysis
- Lexicon-only: ~60% accuracy, misses sarcasm/context
- SnowNLP: maintained poorly, accuracy too low for production
- PaddleNLP: 400MB+ dependency, license restrictions

### ADR-019: Sentiment Results as Grounded Claims

**Decision**: All sentiment statistics (positive_ratio, negative_ratio, topic counts, pain point counts) enter the ClaimsLedger as individual Claims with unique IDs. The Agent's final report must reference these claim IDs — it cannot invent sentiment numbers.

**Rationale**: Extends the existing grounding architecture (ADR-012) to sentiment analysis. Ensures sentiment numbers are traceable to actual computation, not model hallucination. OutputValidator rejects ungrounded sentiment claims.

### ADR-020: Time-Bucket Trend via Deterministic Aggregation

**Decision**: Trend analysis groups data into time buckets (day/week/month) and computes direction (increasing/decreasing/stable) via simple linear regression slope. No LLM involvement in trend computation — only deterministic aggregation.

**Rationale**: Trend direction is a mathematical fact, not a judgment. Using LLM to "analyze trend" risks hallucination. Deterministic computation → grounded claims → LLM narrates the result.
