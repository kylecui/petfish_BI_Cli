from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.agent.tools.sentiment import SentimentAnalysisTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestSentimentAnalysisTool:
    def test_lexicon_mode_returns_claims(self):
        reg = ClaimsRegistry()
        tool = SentimentAnalysisTool(
            data_root=DATA_ROOT,
            registry=reg,
            mode="lexicon",
        )
        result = tool.execute({"source": "crocs_xiaohongshu"})
        assert result.error is None
        assert "claims" in result.value
        assert len(result.value["claims"]) > 0

    def test_sentiment_distribution_sums_to_1(self):
        reg = ClaimsRegistry()
        tool = SentimentAnalysisTool(
            data_root=DATA_ROOT,
            registry=reg,
            mode="lexicon",
        )
        result = tool.execute({"source": "crocs_xiaohongshu"})
        dist = result.value["sentiment_distribution"]
        total = sum(dist.values())
        assert abs(total - 1.0) < 0.01

    def test_writes_to_registry(self):
        reg = ClaimsRegistry()
        tool = SentimentAnalysisTool(
            data_root=DATA_ROOT,
            registry=reg,
            mode="lexicon",
        )
        tool.execute({"source": "crocs_xiaohongshu"})
        assert reg.count >= 3

    def test_tool_protocol_attributes(self):
        tool = SentimentAnalysisTool(
            data_root=DATA_ROOT,
            registry=ClaimsRegistry(),
        )
        assert tool.name == "analyze_sentiment"
        assert "data:read" in tool.capabilities

    def test_unknown_source(self):
        tool = SentimentAnalysisTool(
            data_root=DATA_ROOT,
            registry=ClaimsRegistry(),
        )
        result = tool.execute({"source": "unknown"})
        assert result.error is not None
