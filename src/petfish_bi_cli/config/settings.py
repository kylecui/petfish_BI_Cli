from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelConfig:
    provider: str = "fake"
    name: str = "fake"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None


@dataclass(frozen=True)
class BudgetConfig:
    max_tokens_per_session: int = 100_000
    max_cost_usd: float = 0.50
    max_steps: int = 25


@dataclass(frozen=True)
class DataConfig:
    root: str = "references"
    semantic_dir: str = "references/semantic"


@dataclass(frozen=True)
class VaultConfig:
    enabled: bool = False
    url: str = ""
    token: str | None = None
    api_key_path: str | None = None


@dataclass(frozen=True)
class RagConfig:
    enabled: bool = False
    retriever: str = "crag"
    chunk_size: int = 500
    top_k: int = 5
    documents: tuple = ()


@dataclass(frozen=True)
class Settings:
    model: ModelConfig = field(default_factory=ModelConfig)
    roles: dict[str, ModelConfig] = field(default_factory=dict)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    data: DataConfig = field(default_factory=DataConfig)
    vault: VaultConfig = field(default_factory=VaultConfig)
    rag: RagConfig = field(default_factory=RagConfig)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def primary_model(self) -> ModelConfig:
        if self.roles:
            return self.roles.get("primary", self.model)
        return self.model

    @property
    def fallback_model(self) -> ModelConfig | None:
        if self.roles:
            return self.roles.get("fallback")
        return None


_DEFAULTS: dict[str, Any] = {
    "model": {"provider": "fake", "name": "fake", "temperature": 0.0},
    "budget": {
        "max_tokens_per_session": 100_000,
        "max_cost_usd": 0.50,
        "max_steps": 25,
    },
    "data": {"root": "references", "semantic_dir": "references/semantic"},
}


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings with layered precedence: defaults < .env < YAML < env vars.

    Args:
        config_path: Path to bi_cli.yml. If None, searches configs/bi_cli.yml.
    """
    _load_dotenv()
    path = _resolve_config_path(config_path)
    raw = _deep_merge(_DEFAULTS, {})

    raw = _apply_standard_env(raw)

    if path and path.exists():
        with open(path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
        raw = _deep_merge(raw, yaml_data)

    raw = _apply_env_overrides(raw)

    return _build_settings(raw)


def _resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path is not None:
        return Path(config_path)
    candidates = [
        Path(os.environ.get("BI_CLI_CONFIG", "configs/bi_cli.yml")),
        Path("configs/bi_cli.yml"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_dotenv() -> None:
    search_paths = [
        Path.cwd() / ".env",
        Path(os.environ.get("BI_CLI_CONFIG", "configs/bi_cli.yml")).parent / ".env",
    ]
    for p in search_paths:
        if p.exists():
            _do_load_dotenv(p)
            break


def _do_load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
    except ImportError:
        pass


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if v is None:
            continue
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


_ENV_MAP = {
    "BI_CLI_MODEL_PROVIDER": ("model", "provider"),
    "BI_CLI_MODEL_NAME": ("model", "name"),
    "BI_CLI_MODEL_API_KEY": ("model", "api_key"),
    "BI_CLI_MODEL_BASE_URL": ("model", "base_url"),
    "BI_CLI_MODEL_TEMPERATURE": ("model", "temperature"),
    "BI_CLI_DATA_ROOT": ("data", "root"),
}

_STANDARD_ENV_KEYS = {
    "OPENAI_API_KEY": ("model", "api_key"),
    "ANTHROPIC_API_KEY": ("model", "api_key"),
    "OPENAI_BASE_URL": ("model", "base_url"),
    "ANTHROPIC_BASE_URL": ("model", "base_url"),
}


def _apply_standard_env(raw: dict) -> dict:
    result = _deep_merge({}, raw)
    for env_key, path in _STANDARD_ENV_KEYS.items():
        val = os.environ.get(env_key)
        if not val:
            continue
        _set_nested(result, path, val)
    return result


def _apply_env_overrides(raw: dict) -> dict:
    result = _deep_merge({}, raw)
    for env_key, path in _ENV_MAP.items():
        val = os.environ.get(env_key)
        if not val:
            continue
        if path[-1] == "temperature":
            val = float(val)
        _set_nested(result, path, val)
    return result


def _set_nested(d: dict, path: tuple[str, ...], value: Any) -> None:
    for key in path[:-1]:
        d.setdefault(key, {})
        d = d[key]
    d[path[-1]] = value


def _build_settings(raw: dict) -> Settings:
    model_raw = raw.get("model", {})
    model = ModelConfig(
        provider=model_raw.get("provider", "fake"),
        name=model_raw.get("name", "fake"),
        api_key=model_raw.get("api_key"),
        base_url=model_raw.get("base_url"),
        temperature=model_raw.get("temperature", 0.0),
        max_tokens=model_raw.get("max_tokens"),
    )

    roles: dict[str, ModelConfig] = {}
    for role_name, role_raw in raw.get("roles", {}).items():
        roles[role_name] = ModelConfig(
            provider=role_raw.get("provider", "fake"),
            name=role_raw.get("name", "fake"),
            api_key=role_raw.get("api_key"),
            base_url=role_raw.get("base_url"),
            temperature=role_raw.get("temperature", 0.0),
            max_tokens=role_raw.get("max_tokens"),
        )

    budget_raw = raw.get("budget", {})
    budget = BudgetConfig(
        max_tokens_per_session=budget_raw.get("max_tokens_per_session", 100_000),
        max_cost_usd=budget_raw.get("max_cost_usd", 0.50),
        max_steps=budget_raw.get("max_steps", 25),
    )

    data_raw = raw.get("data", {})
    data = DataConfig(
        root=data_raw.get("root", "references"),
        semantic_dir=data_raw.get("semantic_dir", "references/semantic"),
    )

    vault_raw = raw.get("vault", {})
    vault = VaultConfig(
        enabled=vault_raw.get("enabled", False),
        url=vault_raw.get("url", ""),
        token=vault_raw.get("token"),
        api_key_path=vault_raw.get("api_key_path"),
    )

    rag_raw = raw.get("rag", {})
    rag = RagConfig(
        enabled=rag_raw.get("enabled", False),
        retriever=rag_raw.get("retriever", "crag"),
        chunk_size=rag_raw.get("chunk_size", 500),
        top_k=rag_raw.get("top_k", 5),
        documents=tuple(rag_raw.get("documents", [])),
    )

    return Settings(
        model=model,
        roles=roles,
        budget=budget,
        data=data,
        vault=vault,
        rag=rag,
        raw=raw,
    )
