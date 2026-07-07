from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jieba

POSITIVE_WORDS: frozenset[str] = frozenset(
    {
        "舒服",
        "好穿",
        "好看",
        "百搭",
        "推荐",
        "值得",
        "喜欢",
        "可爱",
        "软",
        "轻",
        "配色",
        "质量好",
        "真香",
        "入手",
        "种草",
        "爱了",
        "满分",
        "完美",
        "高级",
        "质感",
        "满意",
        "不错",
        "好评",
        "回购",
        "上脚",
        "减震",
        "防滑",
        "透气",
        "轻便",
        "颜值",
    }
)

NEGATIVE_WORDS: frozenset[str] = frozenset(
    {
        "磨脚",
        "硬",
        "臭",
        "掉色",
        "开胶",
        "退款",
        "差评",
        "垃圾",
        "踩雷",
        "失望",
        "不值",
        "贵",
        "假",
        "仿",
        "破",
        "裂",
        "脱胶",
        "不舒服",
        "难看",
        "丑",
        "重",
        "闷",
        "不透气",
        "滑",
        "磨",
        "退货",
        "投诉",
        "问题",
        "质量差",
        "假货",
        "坑",
        "避雷",
    }
)

NEGATION_WORDS: frozenset[str] = frozenset(
    {
        "不",
        "没",
        "别",
        "莫",
        "无",
        "非",
        "未",
        "勿",
    }
)


@dataclass(frozen=True)
class SentimentResult:
    text: str
    sentiment: str
    score: float
    matched_positive: tuple[str, ...] = ()
    matched_negative: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()


class LexiconSentimentAnalyzer:
    """jieba + custom lexicon sentiment analyzer for Chinese e-commerce comments."""

    def __init__(self, lexicon_path: Path | None = None):
        self._positive = set(POSITIVE_WORDS)
        self._negative = set(NEGATIVE_WORDS)
        if lexicon_path and lexicon_path.exists():
            self._load_custom_lexicon(lexicon_path)

    @property
    def label(self) -> str:
        return "lexicon"

    def analyze(self, text: str) -> SentimentResult:
        words = list(jieba.cut(text))
        matched_pos: list[str] = []
        matched_neg: list[str] = []

        for i, word in enumerate(words):
            if word in self._positive:
                if _is_negated(words, i):
                    matched_neg.append(word)
                else:
                    matched_pos.append(word)
            elif word in self._negative:
                if _is_negated(words, i):
                    matched_pos.append(word)
                else:
                    matched_neg.append(word)

        pos_count = len(matched_pos)
        neg_count = len(matched_neg)
        total = pos_count + neg_count

        if total == 0:
            return SentimentResult(
                text=text,
                sentiment="neutral",
                score=0.5,
                topics=_extract_topics(text, words),
            )

        score = pos_count / total
        if score >= 0.6:
            sentiment = "positive"
        elif score <= 0.4:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return SentimentResult(
            text=text,
            sentiment=sentiment,
            score=round(score, 3),
            matched_positive=tuple(matched_pos),
            matched_negative=tuple(matched_neg),
            topics=_extract_topics(text, words),
        )

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        return [self.analyze(t) for t in texts]

    def _load_custom_lexicon(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        section = "default"
        for line in text.strip().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.endswith(":"):
                section = stripped[:-1].strip()
            elif section == "positive":
                self._positive.add(stripped)
            elif section == "negative":
                self._negative.add(stripped)


def analyze_lexicon(text: str) -> SentimentResult:
    words = list(jieba.cut(text))
    matched_pos: list[str] = []
    matched_neg: list[str] = []

    for i, word in enumerate(words):
        if word in POSITIVE_WORDS:
            if _is_negated(words, i):
                matched_neg.append(word)
            else:
                matched_pos.append(word)
        elif word in NEGATIVE_WORDS:
            if _is_negated(words, i):
                matched_pos.append(word)
            else:
                matched_neg.append(word)

    pos_count = len(set(matched_pos))
    neg_count = len(set(matched_neg))
    total = pos_count + neg_count

    if total == 0:
        return SentimentResult(
            text=text,
            sentiment="neutral",
            score=0.5,
            topics=_extract_topics(text, words),
        )

    score = pos_count / total
    if score >= 0.6:
        sentiment = "positive"
    elif score <= 0.4:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return SentimentResult(
        text=text,
        sentiment=sentiment,
        score=round(score, 3),
        matched_positive=tuple(matched_pos),
        matched_negative=tuple(matched_neg),
        topics=_extract_topics(text, words),
    )


def _is_negated(words: list[str], idx: int, window: int = 2) -> bool:
    start = max(0, idx - window)
    for j in range(start, idx):
        if words[j] in NEGATION_WORDS:
            return True
    return False


def _extract_topics(text: str, words: list[str]) -> tuple[str, ...]:
    topic_keywords = {
        "价格": ["贵", "便宜", "值", "性价比", "价格", "块钱", "元"],
        "舒适度": ["舒服", "磨脚", "硬", "软", "踩", "脚感"],
        "外观": ["好看", "丑", "颜值", "配色", "款式", "设计"],
        "质量": ["质量", "开胶", "掉色", "破", "裂", "做工"],
        "尺码": ["尺码", "大小", "码", "偏大", "偏小", "合脚"],
        "气味": ["臭", "味道", "气味", "刺鼻"],
    }
    found: set[str] = set()
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text:
                found.add(topic)
                break
    return tuple(found)


def analyze_batch_lexicon(texts: list[str]) -> list[SentimentResult]:
    return [analyze_lexicon(t) for t in texts]


def aggregate_sentiments(results: list[SentimentResult]) -> dict:
    total = len(results)
    if total == 0:
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0, "total": 0}

    pos = sum(1 for r in results if r.sentiment == "positive")
    neg = sum(1 for r in results if r.sentiment == "negative")
    neu = sum(1 for r in results if r.sentiment == "neutral")

    topic_counts: dict[str, int] = {}
    for r in results:
        for t in r.topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1

    return {
        "positive": round(pos / total, 3),
        "negative": round(neg / total, 3),
        "neutral": round(neu / total, 3),
        "total": total,
        "top_topics": sorted(topic_counts.items(), key=lambda x: -x[1])[:5],
    }
