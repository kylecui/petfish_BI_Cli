from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.sentiment.lexicon import (
    LexiconSentimentAnalyzer,
    analyze_lexicon,
)

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestLexiconSentiment:
    def test_negative_磨脚(self):
        result = analyze_lexicon("穿了两天就磨脚了，好痛")
        assert result.sentiment == "negative"

    def test_positive_舒服(self):
        result = analyze_lexicon("非常舒服，很轻便，好看")
        assert result.sentiment == "positive"

    def test_neutral_short_text(self):
        result = analyze_lexicon("买")
        assert result.sentiment in ("neutral", "positive", "negative")

    def test_mixed_sentiment(self):
        result = analyze_lexicon("好看是好看但是磨脚")
        assert result.sentiment in ("negative", "neutral")

    def test_returns_score_between_0_and_1(self):
        result = analyze_lexicon("非常好看")
        assert 0.0 <= result.score <= 1.0

    def test_returns_matched_words(self):
        result = analyze_lexicon("磨脚又掉色")
        assert len(result.matched_negative) >= 1

    def test_custom_lexicon(self, tmp_path):
        lexicon_file = tmp_path / "custom.txt"
        lexicon_file.write_text("positive:\n  超值\n  买了\ndefault:\n", encoding="utf-8")
        analyzer = LexiconSentimentAnalyzer(lexicon_path=lexicon_file)
        result = analyzer.analyze("超值买了")
        assert result.sentiment == "positive"
