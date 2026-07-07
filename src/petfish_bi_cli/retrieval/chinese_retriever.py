from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import jieba

from petfishframework.core.contracts import Retriever
from petfishframework.core.types import Snippet


@dataclass
class ChineseRetriever(Retriever):
    """Keyword-overlap retriever with proper Chinese tokenization.

    Fixes MemoryRetriever's limitation: the default _tokenize() uses
    [a-zA-Z0-9]+ which silently drops all CJK characters. This retriever
    uses jieba for Chinese text, falling back to character-level matching.
    """

    _documents: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._documents.append({"content": content, "metadata": metadata or {}})

    def add_batch(self, contents: list[str], metadata: dict[str, Any] | None = None) -> None:
        for content in contents:
            self.add(content, metadata)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        if not self._documents:
            return []

        query_tokens = _tokenize_chinese(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, Snippet]] = []
        for doc in self._documents:
            content = doc["content"]
            doc_tokens = _tokenize_chinese(content)
            if not doc_tokens:
                continue

            shared = len(query_tokens & doc_tokens)
            if shared == 0:
                continue

            score = shared / max(len(doc_tokens), 1)
            scored.append(
                (
                    score,
                    Snippet(
                        content=content,
                        source=doc["metadata"].get("source", ""),
                        score=score,
                        metadata=doc["metadata"],
                    ),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [snippet for _, snippet in scored[:top_k]]

    @property
    def doc_count(self) -> int:
        return len(self._documents)


def _tokenize_chinese(text: str) -> set[str]:
    """Tokenize text supporting both Chinese (jieba) and alphanumeric."""
    tokens: set[str] = set()
    for word in jieba.cut(text):
        word = word.strip()
        if len(word) >= 2:
            tokens.add(word.lower())
    import re

    for token in re.findall(r"[a-zA-Z0-9]+", text):
        if len(token) >= 2:
            tokens.add(token.lower())
    return tokens
