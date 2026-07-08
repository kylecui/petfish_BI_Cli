from __future__ import annotations

from pathlib import Path

from petfishframework import Agent, YamlPolicy
from petfishframework.permissions.model import DefaultAllowPolicy, PermissionPolicy

from petfish_bi_cli.agent.strategy import BIAgentStrategy
from petfish_bi_cli.agent.tool_factory import ToolFactory
from petfish_bi_cli.config.model_factory import build_model
from petfish_bi_cli.config.settings import Settings, load_settings
from petfish_bi_cli.config.source_registry import SourceRegistry
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

    sources = SourceRegistry(
        config=settings.raw,
        data_root=data_root,
        semantic_dir=semantic_dir,
    )

    all_tools = ToolFactory.build_all(
        sources=sources,
        registry=registry,
        data_root=data_root,
        scripts=ToolFactory.parse_scripts_config(settings.raw),
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
