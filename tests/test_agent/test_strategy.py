from __future__ import annotations

from petfish_bi_cli.agent.strategy import BIAgentStrategy


class TestBIAgentStrategy:
    def test_strategy_inherits_react(self):
        from petfishframework.reasoning.react import ReAct

        strategy = BIAgentStrategy()
        assert isinstance(strategy, ReAct)

    def test_system_prompt_contains_grounding_rules(self):
        strategy = BIAgentStrategy()
        prompt = strategy._system_prompt([])
        assert "BI" in prompt or "bi" in prompt.lower()
        assert "claim" in prompt.lower() or "Tool" in prompt

    def test_system_prompt_contains_data_sources(self):
        strategy = BIAgentStrategy()
        prompt = strategy._system_prompt([])
        assert "jd_products" in prompt or "京东" in prompt
        assert "tmall_products" in prompt or "天猫" in prompt

    def test_system_prompt_has_current_date(self):
        strategy = BIAgentStrategy()
        prompt = strategy._system_prompt([])
        from datetime import date

        assert date.today().isoformat() in prompt

    def test_system_prompt_includes_react_base(self):
        strategy = BIAgentStrategy()
        prompt = strategy._system_prompt([])
        assert "tool" in prompt.lower() or "Tool" in prompt
