from __future__ import annotations

from petfish_bi_cli.config.embedding_selector import (
    EmbeddingSelector,
    FewShotExample,
    IntentFirstSelector,
)


class TestEmbeddingSelector:
    def test_empty_returns_empty(self):
        sel = EmbeddingSelector()
        assert sel.select("query", k=3) == []

    def test_add_and_select(self):
        sel = EmbeddingSelector()
        sel.add(FewShotExample(input="CROCS价格多少", output="lookup result", intent="lookup"))
        results = sel.select("CROCS价格", k=1)
        assert len(results) == 1
        assert results[0].intent == "lookup"

    def test_ranks_by_similarity(self):
        sel = EmbeddingSelector()
        sel.add(FewShotExample(input="天气不错", output="irrelevant", intent=""))
        sel.add(FewShotExample(input="CROCS京东天猫价格对比", output="compare", intent="comparison"))
        sel.add(FewShotExample(input="CROCS均价", output="lookup", intent="lookup"))
        results = sel.select("CROCS价格对比", k=2)
        assert len(results) >= 1
        assert "对比" in results[0].input or "价格" in results[0].input

    def test_top_k_limits(self):
        sel = EmbeddingSelector()
        for i in range(10):
            sel.add(FewShotExample(input=f"CROCS comment {i}", output="r", intent=""))
        results = sel.select("CROCS", k=3)
        assert len(results) <= 3

    def test_no_overlap_returns_empty(self):
        sel = EmbeddingSelector()
        sel.add(FewShotExample(input="天气很好", output="r", intent=""))
        results = sel.select("量子物理", k=3)
        assert len(results) == 0

    def test_chinese_tokenization(self):
        sel = EmbeddingSelector()
        sel.add(FewShotExample(input="洞洞鞋磨脚", output="pain point", intent="sentiment"))
        results = sel.select("磨脚问题", k=1)
        assert len(results) == 1
        assert "磨脚" in results[0].input


class TestIntentFirstSelector:
    def test_intent_match_returns_matched_first(self):
        sel = IntentFirstSelector()
        sel.add(FewShotExample(input="价格", output="l", intent="lookup"))
        sel.add(FewShotExample(input="对比", output="c", intent="comparison"))
        sel.add(FewShotExample(input="均价", output="l2", intent="lookup"))
        results = sel.select("query", intent="lookup", k=2)
        assert all(r.intent == "lookup" for r in results)

    def test_intent_partial_match_fills_with_embedding(self):
        sel = IntentFirstSelector()
        sel.add(FewShotExample(input="CROCS均价", output="l", intent="lookup"))
        sel.add(FewShotExample(input="JD TMALL对比", output="c", intent="comparison"))
        results = sel.select("CROCS", intent="lookup", k=3)
        assert len(results) >= 1
        assert results[0].intent == "lookup"

    def test_no_intent_falls_back_to_embedding(self):
        sel = IntentFirstSelector()
        sel.add(FewShotExample(input="价格", output="l", intent="lookup"))
        results = sel.select("价格", intent=None, k=1)
        assert len(results) == 1

    def test_empty_pool_returns_empty(self):
        sel = IntentFirstSelector()
        assert sel.select("query", intent="lookup", k=3) == []
