from __future__ import annotations

from pathlib import Path

from petfishframework import Agent, YamlPolicy
from petfishframework.permissions.model import DefaultAllowPolicy, PermissionPolicy

from petfish_bi_cli.agent.strategy import BIAgentStrategy
from petfish_bi_cli.agent.tools.cross_source import CrossSourceComparisonTool
from petfish_bi_cli.agent.tools.cross_time import CrossTimeTool
from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
from petfish_bi_cli.agent.tools.load import LoadDataTool
from petfish_bi_cli.agent.tools.sentiment import SentimentAnalysisTool
from petfish_bi_cli.agent.tools.trend import TrendTool
from petfish_bi_cli.config.model_factory import build_model
from petfish_bi_cli.config.settings import Settings, load_settings
from petfish_bi_cli.grounding.claims import ClaimsRegistry

_POLICY_PATH = Path("configs/policy.yml")


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
    sentiment = SentimentAnalysisTool(
        data_root=data_root, registry=registry
    )
    trend = TrendTool(data_root=data_root, registry=registry)
    cross_source = CrossSourceComparisonTool(
        data_root=data_root, registry=registry
    )
    cross_time = CrossTimeTool(data_root=data_root, registry=registry)

    all_tools = (
        explore, load, sentiment, trend, cross_source, cross_time,
    ) + tools

    policy = _load_policy()
    if isinstance(policy, YamlPolicy):
        policy.register_tools(all_tools)

    return Agent(
        model=model,
        reasoning=BIAgentStrategy(),
        tools=all_tools,
        permission_policy=policy,
    )


def _load_policy() -> PermissionPolicy:
    """Load YamlPolicy from configs/policy.yml; fall back to DefaultAllowPolicy."""
    if _POLICY_PATH.exists():
        return YamlPolicy.from_file(str(_POLICY_PATH))
    return DefaultAllowPolicy()
