# Plan: Real Model Integration (M4)

> **Status**: Planning
> **Priority**: 🔴 Blocking — unblocks all real-query usage
> **Depends on**: M-1, M0 (completed)
> **Estimated effort**: 2-3 sessions

## 1. Problem Statement

All 91 existing tests use `FakeModel`. The system cannot answer real BI queries because:

1. `make_bi_agent()` hardcodes `FakeModel()` when no model is passed
2. No settings system — API key, model name, temperature are not configurable
3. No fallback mechanism — if the primary model fails, the entire query fails
4. No smoke test suite — real LLM behavior (tool calling, structured output) is unverified

## 2. Research Basis

| Source | Pattern | Application |
|---|---|---|
| Aider (`.aider.conf.yml`) | Layered config: defaults < YAML < env < CLI flags | `load_settings()` precedence chain |
| Continue (`config.yaml`) | Role-tagged models: `chat` / `edit` / `autocomplete` | `model.roles: {primary, fallback, testing}` |
| OpenHands (`config.toml`) | Named LLM groups with shared defaults | Role inherits from top-level model config |
| LiteLLM | `provider/model_name` identifier | Unified provider routing in `ModelFactory` |
| petfishframework `OpenAIModel.__init__` | `api_key` param > `OPENAI_API_KEY` env | Three-tier key resolution |

## 3. Architecture

### 3.1 Configuration Loading Pipeline

```
configs/bi_cli.yml (YAML defaults)
    ↓ override
Environment variables (BI_CLI_MODEL, OPENAI_API_KEY, ...)
    ↓ override
CLI flags (--model gpt-4o-mini)
    ↓
Settings (frozen dataclass)
```

### 3.2 Model Factory

```
Settings.model
    ↓
ModelFactory.build()
    ├── provider=openai   → OpenAIModel(model, api_key, base_url)
    ├── provider=anthropic → AnthropicModel(model, api_key, base_url)
    └── provider=fake     → FakeModel()
```

### 3.3 Fallback Chain

```
ModelFactory.build_with_fallback(settings.model.roles)
    ↓
try primary model (e.g., claude-sonnet)
    ↓ on RuntimeError (API error / timeout / budget)
try fallback model (e.g., gpt-4o-mini)
    ↓ on failure
raise (no more models to try)
```

## 4. Configuration Format

```yaml
# configs/bi_cli.yml — model section
model:
  provider: openai
  name: gpt-4o
  api_key: null                    # null = read from {PROVIDER}_API_KEY env
  base_url: null                   # null = read from {PROVIDER}_BASE_URL env
  temperature: 0.0
  max_tokens: 4096

  roles:
    primary:
      provider: anthropic
      name: claude-sonnet-4-5-20250929
      temperature: 0.0
    fallback:
      provider: openai
      name: gpt-4o-mini
      temperature: 0.3
    testing:
      provider: fake

budget:
  max_tokens_per_session: 100000
  max_cost_usd: 0.50
  max_steps: 25
```

### Environment Variable Mapping

| Config path | Env var | Notes |
|---|---|---|
| `model.api_key` (openai) | `OPENAI_API_KEY` | Framework built-in |
| `model.api_key` (anthropic) | `ANTHROPIC_API_KEY` | Framework built-in |
| `model.name` | `BI_CLI_MODEL` | Overrides YAML |
| `model.provider` | `BI_CLI_PROVIDER` | Overrides YAML |
| `model.base_url` | `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` | Provider-specific |

## 5. Code Structure

```
src/petfish_bi_cli/config/
├── __init__.py
├── settings.py                    # NEW: load_settings() + Settings dataclass
└── model_factory.py               # NEW: build_model() + build_with_fallback()
```

### 5.1 settings.py

```python
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
class ModelRoles:
    primary: ModelConfig = field(default_factory=ModelConfig)
    fallback: ModelConfig | None = None
    testing: ModelConfig = field(default_factory=lambda: ModelConfig(provider="fake"))


@dataclass(frozen=True)
class BudgetConfig:
    max_tokens_per_session: int = 100000
    max_cost_usd: float = 0.50
    max_steps: int = 25


@dataclass(frozen=True)
class Settings:
    model: ModelConfig = field(default_factory=ModelConfig)
    model_roles: ModelRoles = field(default_factory=ModelRoles)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    data_root: Path = Path("references")
    semantic_dir: Path = Path("references/semantic")


def load_settings(path: str | Path = "configs/bi_cli.yml") -> Settings:
    """Load settings with layered precedence: YAML < env < CLI."""
    yaml_data = _load_yaml(path)
    model = _build_model_config(yaml_data.get("model", {}))
    roles = _build_roles(yaml_data.get("model", {}).get("roles", {}), model)
    budget = _build_budget(yaml_data.get("budget", {}))

    # env overrides
    model = _apply_env_overrides(model)

    return Settings(model=model, model_roles=roles, budget=budget)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _build_model_config(raw: dict) -> ModelConfig:
    return ModelConfig(
        provider=raw.get("provider", "fake"),
        name=raw.get("name", "fake"),
        api_key=raw.get("api_key"),
        base_url=raw.get("base_url"),
        temperature=raw.get("temperature", 0.0),
        max_tokens=raw.get("max_tokens"),
    )


def _build_roles(raw_roles: dict, default_model: ModelConfig) -> ModelRoles:
    def build(key: str) -> ModelConfig:
        raw = raw_roles.get(key)
        if raw is None:
            return default_model if key == "primary" else None  # type: ignore
        return _build_model_config(raw)

    return ModelRoles(
        primary=build("primary") if "primary" in raw_roles else default_model,
        fallback=build("fallback"),
        testing=build("testing"),
    )


def _build_budget(raw: dict) -> BudgetConfig:
    return BudgetConfig(
        max_tokens_per_session=raw.get("max_tokens_per_session", 100000),
        max_cost_usd=raw.get("max_cost_usd", 0.50),
        max_steps=raw.get("max_steps", 25),
    )


def _apply_env_overrides(model: ModelConfig) -> ModelConfig:
    import dataclasses

    updates = {}
    if env_name := os.environ.get("BI_CLI_MODEL"):
        updates["name"] = env_name
    if env_provider := os.environ.get("BI_CLI_PROVIDER"):
        updates["provider"] = env_provider
    if not updates:
        return model
    return dataclasses.replace(model, **updates)
```

### 5.2 model_factory.py

```python
from __future__ import annotations
from typing import Protocol

from petfishframework.core.contracts import ModelAdapter


class ModelAdapterProtocol(Protocol):
    def query(self, request: Any) -> Any: ...


def build_model(config) -> ModelAdapter:
    """Build a single model adapter from ModelConfig."""
    provider = config.provider.lower()

    if provider == "fake":
        from petfishframework.models.fake import FakeModel
        return FakeModel()

    if provider == "openai":
        from petfishframework.models.openai import OpenAIModel
        return OpenAIModel(
            model=config.name,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    if provider == "anthropic":
        from petfishframework.models.anthropic import AnthropicModel
        return AnthropicModel(
            model=config.name,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    raise ValueError(f"Unknown provider: {provider}")


def build_with_fallback(roles) -> ModelAdapter:
    """Build primary model; register fallback for runtime retry."""
    primary = build_model(roles.primary)

    if roles.fallback is None:
        return primary

    fallback = build_model(roles.fallback)
    return FallbackModel(primary=primary, fallback=fallback)


class FallbackModel:
    """Wraps primary + fallback; delegates to fallback on RuntimeError."""

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self.name = f"{getattr(primary, 'name', 'primary')}+fallback"

    def query(self, request):
        try:
            return self._primary.query(request)
        except (RuntimeError, Exception) as exc:
            if self._fallback is None:
                raise
            return self._fallback.query(request)
```

### 5.3 framework.py Modification

```python
# framework.py — before (M0)
def make_bi_agent(model=None, ...) -> Agent:
    if model is None:
        model = FakeModel()
    ...

# framework.py — after (M4)
def make_bi_agent(
    settings: Settings | None = None,
    registry: ClaimsRegistry | None = None,
    **overrides,
) -> Agent:
    if settings is None:
        settings = load_settings()
    model = build_with_fallback(settings.model_roles)
    ...
```

## 6. TDD Task Breakdown

| Task ID | Description | Test (RED) | Implementation (GREEN) |
|---|---|---|---|
| M4-T001 | Settings loads YAML | `test_settings_loads_yaml` — assert `settings.model.name == "gpt-4o"` from fixture YAML | `settings.py: load_settings()` |
| M4-T002 | Env overrides YAML | `test_env_overrides_yaml` — set `BI_CLI_MODEL=gpt-4o-mini`, assert override | `_apply_env_overrides()` |
| M4-T003 | Missing config file returns defaults | `test_missing_config_defaults` — non-existent path, assert `provider == "fake"` | `_load_yaml()` returns `{}` |
| M4-T004 | ModelFactory builds OpenAI | `test_model_factory_openai` — `provider=openai`, assert `isinstance(result, OpenAIModel)` | `model_factory.py: build_model()` |
| M4-T005 | ModelFactory builds Anthropic | `test_model_factory_anthropic` — `provider=anthropic` | Same function |
| M4-T006 | ModelFactory builds Fake | `test_model_factory_fake` — `provider=fake` | Same function |
| M4-T007 | ModelFactory unknown provider raises | `test_unknown_provider_raises` — `provider=unknown`, assert `ValueError` | Same function |
| M4-T008 | Fallback chain retries on failure | `test_fallback_on_runtime_error` — primary raises `RuntimeError`, assert fallback called | `FallbackModel` |
| M4-T009 | Fallback returns primary on success | `test_no_fallback_on_success` — primary succeeds, assert fallback not called | Same class |
| M4-T010 | make_bi_agent uses settings | `test_make_bi_agent_from_settings` — pass Settings with `provider=fake`, assert FakeModel | `framework.py` refactor |
| M4-T011 | Budget config maps to framework Budget | `test_budget_from_settings` — assert `Budget(max_tokens=...)` constructed | Budget integration |
| M4-T012 | Real-model smoke test | `test_smoke_real_model` — `@pytest.mark.integration`, query "JD均价", assert `status == "ok"` | Smoke test file |

## 7. Dependencies

No new Python dependencies. `petfishframework[openai]` and `[anthropic]` are already optional extras:

```bash
uv sync --extra dev --extra openai     # development
uv sync --extra dev --extra anthropic  # if using Anthropic
```

## 8. Integration Points

| Component | Change | Risk |
|---|---|---|
| `framework.py: make_bi_agent()` | Signature changes from `model=None` to `settings=None` | LOW — callers in tests updated |
| `application.py: BIApplication.__init__()` | Accepts `settings` param, passes to `make_bi_agent()` | LOW |
| `main.py (CLI)` | Loads settings from `--config` flag or default path | LOW |
| `web.py (FastAPI)` | Loads settings from `BI_CLI_CONFIG` env or default | LOW |

## 9. ADR

### ADR-016: Layered Settings with YAML + Env + CLI Precedence

**Decision**: Settings follow Aider's layered precedence model: `defaults < configs/bi_cli.yml < env vars < CLI flags`.

**Rationale**: Industry standard (Aider, Continue, OpenHands all use this). Predictable for users. Allows CI to override via env, developers to override via flags, teams to share via YAML in git.

**Alternatives considered**:
- `.env` only (simpler but no structured config, no role-based models)
- `pydantic-settings` (adds dependency, overkill for 6 config fields)
- Hardcoded defaults + env only (no YAML, poor UX for multi-field config)

### ADR-017: Model Fallback Chain

**Decision**: `ModelFactory.build_with_fallback()` wraps primary + fallback. On `RuntimeError` (API error, timeout), delegates to fallback model.

**Rationale**: API failures are common (rate limits, downtime). A degraded answer from gpt-4o-mini is better than no answer. Fallback is opt-in (if `roles.fallback` is None, no wrapping).

**Alternatives considered**:
- Retry same model with exponential backoff (delays, doesn't solve downtime)
- Circuit breaker pattern (too complex for v1)
- No fallback (poor reliability)
