from __future__ import annotations

from pathlib import Path

from petfishframework import Agent
from petfishframework.models.fake import FakeModel

from petfish_bi_cli.agent.strategy import BIAgentStrategy
from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry


def make_bi_agent(
    model=None,
    tools: tuple = (),
    data_root: Path | None = None,
    semantic_dir: Path | None = None,
    registry: ClaimsRegistry | None = None,
) -> Agent:
    if model is None:
        model = FakeModel()
    if registry is None:
        registry = ClaimsRegistry()
    if data_root is None:
        data_root = Path("references")
    if semantic_dir is None:
        semantic_dir = data_root / "semantic"

    explore = ExploreDataSourcesTool(semantic_dir=semantic_dir)
    load = LoadDataTool(data_root=data_root, registry=registry)

    all_tools = (explore, load) + tools
    return Agent(
        model=model,
        reasoning=BIAgentStrategy(),
        tools=all_tools,
    )
