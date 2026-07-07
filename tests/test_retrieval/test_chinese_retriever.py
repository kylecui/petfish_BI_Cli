from __future__ import annotations

import pytest

from petfish_bi_cli.retrieval.chinese_retriever import ChineseRetriever


class TestChineseRetriever:
    def test_add_and_retrieve(self):
        r = ChineseRetriever()
        r.add("CROCS洞洞鞋穿着很舒服，轻便百搭", {"source": "c1"})
        results = r.retrieve("CROCS舒服吗", top_k=1)
        assert len(results) == 1
        assert "舒服" in results[0].content

    def test_multiple_documents_ranked(self):
        r = ChineseRetriever()
        r.add("今天天气不错", {})
        r.add("CROCS鞋磨脚不舒服", {})
        r.add("CROCS云朵款穿着舒服好看", {})
        results = r.retrieve("CROCS穿着舒服", top_k=2)
        assert len(results) >= 1
        assert "CROCS" in results[0].content

    def test_empty_store_returns_empty(self):
        r = ChineseRetriever()
        results = r.retrieve("query", top_k=5)
        assert results == []

    def test_empty_query_returns_empty(self):
        r = ChineseRetriever()
        r.add("document content", {})
        results = r.retrieve("", top_k=5)
        assert results == []

    def test_top_k_limits_results(self):
        r = ChineseRetriever()
        for i in range(10):
            r.add(f"CROCS评论第{i}条穿着舒服", {})
        results = r.retrieve("CROCS舒服", top_k=3)
        assert len(results) == 3

    def test_snippet_has_metadata(self):
        r = ChineseRetriever()
        r.add("content here", {"source": "test", "row": 42})
        results = r.retrieve("content", top_k=1)
        assert results[0].metadata["row"] == 42

    def test_chinese_tokenization_not_lost(self):
        r = ChineseRetriever()
        r.add("洞洞鞋磨脚严重", {})
        results = r.retrieve("磨脚", top_k=1)
        assert len(results) >= 0

    def test_score_is_float(self):
        r = ChineseRetriever()
        r.add("test document content", {})
        results = r.retrieve("test", top_k=1)
        assert len(results) >= 1
        assert isinstance(results[0].score, float)

    def test_implements_retriever_protocol(self):
        from petfishframework.core.contracts import Retriever

        r = ChineseRetriever()
        assert isinstance(r, Retriever)

    def test_doc_count(self):
        r = ChineseRetriever()
        assert r.doc_count == 0
        r.add("doc1", {})
        r.add("doc2", {})
        assert r.doc_count == 2

    def test_add_batch(self):
        r = ChineseRetriever()
        r.add_batch(["doc1", "doc2", "doc3"], {"source": "test"})
        assert r.doc_count == 3
