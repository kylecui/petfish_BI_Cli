from __future__ import annotations

from dataclasses import dataclass, field

_BI_CUSTOM_WORDS = [
    "洞洞鞋",
    "磨脚",
    "平替",
    "云朵款",
    "好穿",
    "百搭",
    "掉色",
    "开胶",
    "退款",
    "舒服",
    "好看",
    "推荐",
    "京东",
    "天猫",
    "小红书",
    "均价",
    "价格差异",
]

_jieba_initialized = False


def _ensure_jieba_words() -> None:
    global _jieba_initialized
    if _jieba_initialized:
        return
    import jieba

    for w in _BI_CUSTOM_WORDS:
        jieba.add_word(w)
    _jieba_initialized = True


@dataclass(frozen=True)
class FewShotExample:
    input: str
    output: str
    intent: str = ""
    embedding: tuple[float, ...] = field(default_factory=tuple)


class EmbeddingSelector:
    """Selects few-shot examples by keyword overlap similarity.

    Phase 1: jieba tokenization + Jaccard similarity (no external deps).
    Phase 2: upgrade to sentence-transformers embeddings when available.
    """

    def __init__(self) -> None:
        self._examples: list[FewShotExample] = []
        self._token_cache: dict[str, set[str]] = {}

    def add(self, example: FewShotExample) -> None:
        self._examples.append(example)
        self._token_cache[example.input] = self._tokenize(example.input)

    def select(self, query: str, k: int = 3) -> list[FewShotExample]:
        if not self._examples:
            return []
        query_tokens = self._tokenize(query)
        scored = [
            (self._jaccard(query_tokens, self._token_cache[ex.input]), ex) for ex in self._examples
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for score, ex in scored[:k] if score > 0]

    def _tokenize(self, text: str) -> set[str]:
        _ensure_jieba_words()
        import jieba

        words = [w for w in jieba.cut(text) if w.strip()]
        tokens: set[str] = set()
        for w in words:
            if w in (" ", "", "？", "的", "了", "是", "在"):
                continue
            tokens.add(w)
            if len(w) >= 3:
                for i in range(len(w) - 1):
                    tokens.add(w[i : i + 2])
        return tokens

    def _jaccard(self, a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        intersection = a & b
        union = a | b
        return len(intersection) / len(union) if union else 0.0


class IntentFirstSelector:
    """Phase 1 fallback: intent-first selection with embedding tiebreaker."""

    def __init__(self) -> None:
        self._embedding = EmbeddingSelector()

    def add(self, example: FewShotExample) -> None:
        self._embedding.add(example)

    def select(self, query: str, intent: str | None = None, k: int = 3) -> list[FewShotExample]:
        if not self._embedding._examples:
            return []
        if intent:
            matched = [ex for ex in self._embedding._examples if ex.intent == intent]
            if len(matched) >= k:
                return matched[:k]
            remaining = k - len(matched)
            others = self._embedding.select(query, remaining)
            seen = {ex.input for ex in matched}
            extras = [ex for ex in others if ex.input not in seen]
            return matched + extras[:remaining]
        return self._embedding.select(query, k)
