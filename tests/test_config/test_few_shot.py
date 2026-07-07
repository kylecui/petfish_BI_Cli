from __future__ import annotations

from petfish_bi_cli.config.prompt_manager import FewShotSelector, PromptManager


class TestFewShotSelector:
    def test_select_by_intent_comparison(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        (pool / "comparison.txt").write_text(
            "intent: comparison\nUser: JD vs TMALL价格\nThought: 需要对比",
            encoding="utf-8",
        )
        (pool / "lookup.txt").write_text(
            "intent: lookup\nUser: JD均价\nThought: 需要查询",
            encoding="utf-8",
        )
        selector = FewShotSelector(pool_dir=pool)
        result = selector.select(query="JD和TMALL价格差异", intent="comparison", k=1)
        assert "对比" in result or "comparison" in result

    def test_select_by_intent_lookup(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        (pool / "lookup.txt").write_text(
            "intent: lookup\nUser: JD均价\nThought: 查询",
            encoding="utf-8",
        )
        (pool / "comparison.txt").write_text(
            "intent: comparison\nUser: 对比\nThought: 对比",
            encoding="utf-8",
        )
        selector = FewShotSelector(pool_dir=pool)
        result = selector.select(query="JD卖多少钱", intent="lookup", k=1)
        assert "查询" in result

    def test_fallback_when_intent_not_found(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        (pool / "lookup.txt").write_text("intent: lookup\n示例", encoding="utf-8")
        selector = FewShotSelector(pool_dir=pool)
        result = selector.select(query="query", intent="comparison", k=1)
        assert len(result) > 0

    def test_empty_pool_returns_empty(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        selector = FewShotSelector(pool_dir=pool)
        result = selector.select(query="query", intent="lookup", k=3)
        assert result == ""

    def test_k_limits_results(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        for i in range(5):
            (pool / f"ex{i}.txt").write_text(
                f"intent: lookup\nExample {i}", encoding="utf-8"
            )
        selector = FewShotSelector(pool_dir=pool)
        result = selector.select(query="query", intent="lookup", k=2)
        assert result.count("Example") <= 2

    def test_keyword_similarity_scoring(self, tmp_path):
        pool = tmp_path / "pool"
        pool.mkdir()
        (pool / "a.txt").write_text("CROCS洞洞鞋价格查询", encoding="utf-8")
        (pool / "b.txt").write_text("天气真好出门走走", encoding="utf-8")
        selector = FewShotSelector(pool_dir=pool, strategy="keyword")
        result = selector.select(query="CROCS洞洞鞋多少钱", intent=None, k=1)
        assert "CROCS" in result or "洞洞鞋" in result


class TestPromptManagerEnhanced:
    def test_loads_versioned_prompt(self, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Version 2.0 BI prompt", encoding="utf-8")

        mgr = PromptManager({
            "system_prompt": {
                "file": str(prompt_file),
                "version": "2.0",
            },
        })
        prompt = mgr.load_system_prompt()
        assert "Version 2.0" in prompt

    def test_few_shot_integration(self, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("BI prompt", encoding="utf-8")
        pool = tmp_path / "pool"
        pool.mkdir()
        (pool / "lookup.txt").write_text(
            "intent: lookup\nUser: JD均价\nThought: 查",
            encoding="utf-8",
        )

        mgr = PromptManager({
            "system_prompt": {"file": str(prompt_file)},
            "few_shot": {
                "mode": "dynamic",
                "pool_dir": str(pool),
                "k": 1,
                "selection": "intent-first",
            },
        })
        system = mgr.load_system_prompt()
        few_shot = mgr.select_few_shot("JD均价", intent="lookup")
        assert "BI" in system
        assert "查" in few_shot
