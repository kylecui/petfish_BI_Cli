from __future__ import annotations

from dataclasses import dataclass, field


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
            (self._jaccard(query_tokens, self._token_cache[ex.input]), ex)
            for ex in self._examples
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:k] if scored[0][0] > 0]

    def _tokenize(self, text: str) -> set[str]:
        import jieba
        tokens = set(jieba.cut(text))
        tokens.discard(" ")
        tokens.discard("")
        tokens.discard("？")
        tokens.discard("的")
        tokens.discard("了")
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
