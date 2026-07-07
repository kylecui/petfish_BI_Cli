from __future__ import annotations

import json
from dataclasses import dataclass

from petfishframework.core.contracts import ModelAdapter

from petfish_bi_cli.sentiment.lexicon import SentimentResult

SENTIMENT_PROMPT = """分析以下小红书评论的情感倾向。每条评论返回JSON：
{"sentiment": "positive|negative|neutral", "topics": ["价格","舒适度",...], "pain_points": ["磨脚",...]}

评论列表：
"""


@dataclass
class LLMSentimentBatch:
    model: ModelAdapter
    batch_size: int = 50

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        results: list[SentimentResult] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            results.extend(self._process_batch(batch))
        return results

    def _process_batch(self, batch: list[str]) -> list[SentimentResult]:
        from petfishframework.core.types import Message, ModelRequest, Role

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(batch))
        prompt = SENTIMENT_PROMPT + numbered + "\n\n返回JSON数组，每个元素对应一条评论。"

        request = ModelRequest(
            messages=(Message(role=Role.USER, content=prompt),),
            temperature=0.0,
        )
        response = self.model.query(request)
        return self._parse_response(response.content, batch)

    def _parse_response(self, content: str, batch: list[str]) -> list[SentimentResult]:
        results: list[SentimentResult] = []
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, list):
                parsed = [parsed]
            for i, item in enumerate(parsed):
                text = batch[i] if i < len(batch) else ""
                sentiment = item.get("sentiment", "neutral")
                if sentiment not in ("positive", "negative", "neutral"):
                    sentiment = "neutral"
                results.append(
                    SentimentResult(
                        text=text,
                        sentiment=sentiment,
                        score=1.0
                        if sentiment == "positive"
                        else 0.0
                        if sentiment == "negative"
                        else 0.5,
                        topics=tuple(item.get("topics", [])),
                    )
                )
        except (json.JSONDecodeError, IndexError):
            for text in batch:
                results.append(SentimentResult(text=text, sentiment="neutral", score=0.5))
        return results
