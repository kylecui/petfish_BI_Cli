from __future__ import annotations

import time

from petfish_bi_cli.config.prompt_manager import PromptManager


class TestPromptManager:
    def test_load_system_prompt_from_config(self, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("You are a BI agent. Version 2.", encoding="utf-8")

        mgr = PromptManager(
            {
                "system_prompt": {"file": str(prompt_file)},
            }
        )
        assert "BI agent" in mgr.load_system_prompt()

    def test_returns_default_when_file_missing(self):
        mgr = PromptManager({"system_prompt": {"file": "nonexistent.md"}})
        prompt = mgr.load_system_prompt()
        assert "BI" in prompt or "bi" in prompt.lower()

    def test_hot_reload_detects_file_change(self, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Version 1", encoding="utf-8")

        mgr = PromptManager({"system_prompt": {"file": str(prompt_file)}})
        assert "Version 1" in mgr.load_system_prompt()

        time.sleep(0.1)
        prompt_file.write_text("Version 2", encoding="utf-8")
        assert "Version 2" in mgr.load_system_prompt()

    def test_few_shot_off_returns_empty(self):
        mgr = PromptManager({"few_shot": {"mode": "off"}})
        assert mgr.select_few_shot("any query") == ""

    def test_few_shot_no_config_returns_empty(self):
        mgr = PromptManager({})
        assert mgr.select_few_shot("any query") == ""

    def test_few_shot_static_mode(self, tmp_path):
        pool_dir = tmp_path / "few_shot"
        pool_dir.mkdir()
        (pool_dir / "comparison.yml").write_text(
            "input: JD和TMALL价格差异\noutput: compare action\nintent: comparison",
            encoding="utf-8",
        )

        mgr = PromptManager(
            {
                "few_shot": {
                    "mode": "static",
                    "pool_dir": str(pool_dir),
                    "k": 3,
                    "selection": "intent-first",
                },
            }
        )
        result = mgr.select_few_shot("query")
        assert len(result) > 0

    def test_few_shot_intent_first_selection(self, tmp_path):
        pool_dir = tmp_path / "few_shot"
        pool_dir.mkdir()
        (pool_dir / "comparison.txt").write_text(
            "input: JD和TMALL价格差异\noutput: compare\nintent: comparison",
            encoding="utf-8",
        )
        (pool_dir / "lookup.txt").write_text(
            "input: JD均价多少\noutput: lookup\nintent: lookup",
            encoding="utf-8",
        )

        mgr = PromptManager(
            {
                "few_shot": {
                    "mode": "dynamic",
                    "pool_dir": str(pool_dir),
                    "k": 1,
                    "selection": "intent-first",
                },
            }
        )
        result = mgr.select_few_shot("query", intent="comparison")
        assert "compare" in result

    def test_caches_file_content(self, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Cache test", encoding="utf-8")

        mgr = PromptManager({"system_prompt": {"file": str(prompt_file)}})
        first = mgr.load_system_prompt()
        second = mgr.load_system_prompt()
        assert first == second
