from __future__ import annotations

from pathlib import Path

from petfishframework import Agent

from petfish_bi_cli.agent.strategy import BIAgentStrategy
from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.config.model_factory import build_model
from petfish_bi_cli.config.settings import Settings, load_settings
from petfish_bi_cli.grounding.claims import ClaimsRegistry


def make_bi_agent(
    model=None,
    tools: tuple = (),
    data_root: Path | None = None,
    semantic_dir: Path | None = None,
    registry: ClaimsRegistry | None = None,
    settings: Settings | None = None,
) -> Agent:
    if settings is None:
        settings = load_settings()
    if model is None:
        model = build_model(settings)
    if registry is None:
        registry = ClaimsRegistry()
    if data_root is None:
        data_root = Path(settings.data.root)
    if semantic_dir is None:
        semantic_dir = Path(settings.data.semantic_dir)

    explore = ExploreDataSourcesTool(semantic_dir=semantic_dir)
    load = LoadDataTool(data_root=data_root, registry=registry)

    all_tools = (explore, load) + tools
    return Agent(
        model=model,
        reasoning=BIAgentStrategy(),
        tools=all_tools,
    )
