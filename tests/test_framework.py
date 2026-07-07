from __future__ import annotations

from pathlib import Path

from petfishframework import Agent
from petfishframework.models.fake import FakeModel

from petfish_bi_cli.framework import make_bi_agent
from petfish_bi_cli.grounding.claims import ClaimsRegistry

PROJECT_ROOT = Path(__file__).parent.parent


class TestMakeBIAgent:
    def test_returns_agent(self):
        agent = make_bi_agent(
            model=FakeModel(),
            data_root=PROJECT_ROOT / "references",
            semantic_dir=PROJECT_ROOT / "references" / "semantic",
            registry=ClaimsRegistry(),
        )
        assert isinstance(agent, Agent)

    def test_agent_has_tools(self):
        agent = make_bi_agent(
            model=FakeModel(),
            data_root=PROJECT_ROOT / "references",
            semantic_dir=PROJECT_ROOT / "references" / "semantic",
        )
        tool_names = [t.name for t in agent.tools]
        assert "explore_data_sources" in tool_names
        assert "load_data" in tool_names

    def test_agent_uses_bi_strategy(self):
        from petfish_bi_cli.agent.strategy import BIAgentStrategy

        agent = make_bi_agent(
            model=FakeModel(),
            data_root=PROJECT_ROOT / "references",
            semantic_dir=PROJECT_ROOT / "references" / "semantic",
        )
        assert isinstance(agent.reasoning, BIAgentStrategy)

    def test_agent_is_frozen(self):
        agent = make_bi_agent(model=FakeModel())
        try:
            agent.model = FakeModel()
            raise AssertionError("Should have failed")
        except AttributeError:
            pass
