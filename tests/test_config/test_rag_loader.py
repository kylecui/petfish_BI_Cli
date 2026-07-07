from __future__ import annotations

import pytest

from petfish_bi_cli.config.rag_loader import build_retriever
from petfishframework.retrieval import CRAGRetriever


class TestBuildRetriever:
    def test_empty_config_returns_none(self):
        result = build_retriever({})
        assert result is None

    def test_no_retrievers_returns_none(self):
        result = build_retriever({"retrievers": {}})
        assert result is None

    def test_builds_crag_retriever(self):
        result = build_retriever({
            "retrievers": {
                "test": {
                    "type": "crag",
                    "source": "test_source",
                    "documents": [
                        {"content": "CROCS鞋很舒服", "metadata": {}},
                        {"content": "磨脚问题严重", "metadata": {}},
                    ],
                },
            },
        })
        assert result is not None
        assert isinstance(result, CRAGRetriever)

    def test_retriever_can_search(self):
        retriever = build_retriever({
            "retrievers": {
                "test": {
                    "type": "crag",
                    "source": "test",
                    "documents": [
                        {"content": "CROCS洞洞鞋穿着舒服好看", "metadata": {"id": 1}},
                    ],
                },
            },
        })
        assert retriever is not None
        results = retriever.retrieve("CROCS舒服", top_k=1)
        assert len(results) >= 1

    def test_multiple_retrievers_merge(self):
        retriever = build_retriever({
            "retrievers": {
                "comments": {
                    "type": "crag",
                    "source": "c1",
                    "documents": [{"content": "评论A", "metadata": {}}],
                },
                "products": {
                    "type": "crag",
                    "source": "p1",
                    "documents": [{"content": "商品B", "metadata": {}}],
                },
            },
        })
        assert retriever is not None

    def test_empty_documents_returns_none(self):
        result = build_retriever({
            "retrievers": {
                "test": {
                    "type": "crag",
                    "source": "test",
                    "documents": [],
                },
            },
        })
        assert result is None
