# Plan: Configurable RAG / MCP / Prompts (M6)

> **Status**: Planning
> **Priority**: 🟡 Medium — unblocks extensibility
> **Depends on**: M4 (shared Settings); M5 (sentiment reuses prompt manager)
> **Estimated effort**: 4-5 sessions

## 1. Problem Statement

Currently, every configuration change requires code modification:

| Need | Current | Pain |
|---|---|---|
| Add MCP server (web search, DB) | Write Python code in `framework.py` | Non-developers can't add tools |
| Add RAG for CROCS comments | `MemoryRetriever._tokenize()` can't handle Chinese; no auto-wiring | Manual embedding pipeline |
| Change system prompt | Edit `src/.../prompts/system_prompt.md`, restart | No hot-reload, no A/B test, no regression |
| Switch model | Hardcoded `FakeModel()` in `framework.py` | Can't test with real model without code change |
| Add few-shot example | Edit static file | Not selected by query intent |

## 2. Research Basis

### MCP Configuration

| Source | Format | Key insight |
|---|---|---|
| Claude Desktop `claude_desktop_config.json` | JSON, `mcpServers` root key, `command/args/env` | Industry standard |
| Cursor `.cursor/mcp.json` | Same as Claude + `${env:VAR}` interpolation | Project + global scope |
| Continue `config.yaml` | YAML list, `name/command/args/env/type` | Most ergonomic for YAML-first projects |
| petfishframework `mcp/client.py` | `connect_stdio(command, args, env)` → `MCPClient.discover_tools()` | **Already fully built** — just needs YAML → connect_stdio adapter |

**Decision**: Adopt Continue-style YAML list format (aligns with our `configs/bi_cli.yml`). Use `connect_stdio()` for stdio servers.

### RAG Configuration

| Source | Format | Key insight |
|---|---|---|
| LlamaIndex `Settings` | Python objects, `ServiceContext` | Programmatic, not declarative |
| LangChain `RunnableConfig` | Dict-based, chainable | Too flexible, hard to validate |
| petfishframework CRAG | `CRAGRetriever(base_retriever, evaluator, web_search)` | **Already fully built** — needs base retriever with Chinese support |
| MemoryRetriever | `re.findall(r"[a-zA-Z0-9]+")` tokenizer | **Cannot tokenize Chinese** — critical limitation |

**Decision**: Build `ChineseEmbeddingRetriever` with `sentence-transformers` + BGE-zh. Wrap in `CRAGRetriever`. Configure via YAML.

### Prompt Management

| Source | Approach | Key insight |
|---|---|---|
| PromptLayer | Cloud SaaS, API-based | Not suitable for CLI |
| LangSmith Hub | Cloud, file-cached | Requires LangSmith account |
| DSPy | Programmatic, "compile" prompts | Too heavyweight |
| Promptfoo | YAML-based testing, CLI-native | ✅ Perfect for regression testing |
| promptfile | YAML files, Git-native | ✅ Perfect for version control |

**Decision**: YAML-based prompt files + mtime hot-reload. Promptfoo for regression testing (optional). Dynamic few-shot via intent-first selection.

## 3. Unified Configuration Format

```yaml
# configs/bi_cli.yml — single source of truth
# ============================================================

# --- Model (from M4) ---
model:
  provider: openai
  name: gpt-4o
  roles:
    primary: { provider: anthropic, name: claude-sonnet-4-5-20250929, temperature: 0.0 }
    fallback: { provider: openai, name: gpt-4o-mini, temperature: 0.3 }
    testing: { provider: fake }

budget:
  max_tokens_per_session: 100000
  max_cost_usd: 0.50
  max_steps: 25

# --- MCP Servers (M6-A) ---
mcp:
  auto_load: true
  servers:
    filesystem:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./references"]
    # web_search:
    #   command: npx
    #   args: ["-y", "@anthropic/mcp-web-search"]
    #   env:
    #     ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

# --- RAG Retrieval (M6-B) ---
retrieval:
  enabled: true
  retrievers:
    crocs_comments:
      type: crag
      source: crocs_xiaohongshu
      index:
        field: 评论内容
        embedding_model: BAAI/bge-base-zh-v1.5
      retrieval:
        top_k: 5
        relevance_threshold: 0.5
    product_titles:
      type: simple
      source: tmall_products
      index:
        field: title

# --- Prompt Management (M6-C) ---
prompts:
  system_prompt:
    file: configs/prompts/system_prompt.md
    version: "1.1.0"
  few_shot:
    mode: dynamic                          # dynamic | static | off
    pool_dir: configs/prompts/few_shot/
    k: 3
    selection: intent-first                # intent-first | embedding-sim
    fallback: static

# --- Data ---
data:
  root: references/
  semantic_dir: references/semantic/

# --- Analysis (from M5) ---
analysis:
  sentiment:
    mode: hybrid
```

## 4. Architecture

```
configs/bi_cli.yml
        │
        ▼
┌──────────────────┐
│  load_settings() │  ← validates YAML, applies env overrides
└──────┬───────────┘
       │ Settings dataclass
       ├──────────────────────────────────────────────────┐
       ▼                  ▼                 ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐
│ModelFactory │  │  MCPLoader   │  │  RAGLoader  │  │PromptMgr   │
│→ ModelAdapter│  │→ list[Tool]  │  │→ Retriever  │  │→ Strategy  │
└──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └─────┬──────┘
       │                │                  │               │
       └────────────────┴──────────────────┴───────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  make_bi_agent() │  ← assembles all components
              └──────────────────┘
                        │
                        ▼
                    Agent + Session
```

## 5. Component Design

### 5.1 Settings Loader

```python
# src/petfish_bi_cli/config/settings.py
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
class MCPConfig:
    auto_load: bool = False
    servers: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalConfig:
    enabled: bool = False
    retrievers: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptConfig:
    system_prompt_file: str = "configs/prompts/system_prompt.md"
    system_prompt_version: str = "1.0.0"
    few_shot_mode: str = "static"
    few_shot_pool_dir: str = "configs/prompts/few_shot/"
    few_shot_k: int = 3
    few_shot_selection: str = "intent-first"


@dataclass(frozen=True)
class Settings:
    model: ModelConfig = field(default_factory=ModelConfig)
    model_roles: dict[str, ModelConfig] = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    prompts: PromptConfig = field(default_factory=PromptConfig)
    data_root: Path = Path("references")
    semantic_dir: Path = Path("references/semantic")
    analysis: dict[str, Any] = field(default_factory=dict)


def load_settings(path: str | Path = "configs/bi_cli.yml") -> Settings:
    """Load settings from YAML, apply env overrides, return frozen Settings."""
    config_path = Path(path)
    if not config_path.exists():
        return Settings()  # defaults (all FakeModel, no MCP, no RAG)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    model_cfg = _build_model_config(raw.get("model", {}))
    roles = {name: _build_model_config(cfg) for name, cfg in raw.get("model", {}).get("roles", {}).items()}
    mcp_cfg = _build_mcp_config(raw.get("mcp", {}))
    retrieval_cfg = _build_retrieval_config(raw.get("retrieval", {}))
    prompt_cfg = _build_prompt_config(raw.get("prompts", {}))

    return Settings(
        model=model_cfg,
        model_roles=roles,
        budget=raw.get("budget", {}),
        mcp=mcp_cfg,
        retrieval=retrieval_cfg,
        prompts=prompt_cfg,
        data_root=Path(raw.get("data", {}).get("root", "references")),
        semantic_dir=Path(raw.get("data", {}).get("semantic_dir", "references/semantic")),
        analysis=raw.get("analysis", {}),
    )


def _build_model_config(raw: dict) -> ModelConfig:
    return ModelConfig(
        provider=raw.get("provider", "fake"),
        name=raw.get("name", "fake"),
        api_key=raw.get("api_key"),
        base_url=raw.get("base_url"),
        temperature=raw.get("temperature", 0.0),
        max_tokens=raw.get("max_tokens"),
    )


def _build_mcp_config(raw: dict) -> MCPConfig:
    return MCPConfig(auto_load=raw.get("auto_load", False), servers=raw.get("servers", {}))


def _build_retrieval_config(raw: dict) -> RetrievalConfig:
    return RetrievalConfig(enabled=raw.get("enabled", False), retrievers=raw.get("retrievers", {}))


def _build_prompt_config(raw: dict) -> PromptConfig:
    sp = raw.get("system_prompt", {})
    fs = raw.get("few_shot", {})
    return PromptConfig(
        system_prompt_file=sp.get("file", "configs/prompts/system_prompt.md"),
        system_prompt_version=sp.get("version", "1.0.0"),
        few_shot_mode=fs.get("mode", "static"),
        few_shot_pool_dir=fs.get("pool_dir", "configs/prompts/few_shot/"),
        few_shot_k=fs.get("k", 3),
        few_shot_selection=fs.get("selection", "intent-first"),
    )
```

### 5.2 MCP Loader

```python
# src/petfish_bi_cli/config/mcp_loader.py
from __future__ import annotations
import os
import re
from typing import Any

from petfishframework.mcp.wrapper import MCPToolWrapper


def load_mcp_tools(config: dict) -> list[MCPToolWrapper]:
    """Connect to MCP servers from config, return list of framework Tools."""
    if not config.get("auto_load", False):
        return []

    from petfishframework.mcp.client import connect_stdio

    servers = config.get("servers", {})
    tools: list[MCPToolWrapper] = []

    for name, cfg in servers.items():
        transport = cfg.get("transport", "stdio")
        if transport != "stdio":
            continue  # Phase 2: HTTP/SSE support

        try:
            client = connect_stdio(
                command=cfg["command"],
                args=cfg.get("args", []),
                env=_resolve_env(cfg.get("env", {})) or None,
            )
            tools.extend(client.discover_tools())
        except Exception as exc:
            import warnings
            warnings.warn(f"MCP server '{name}' failed to connect: {exc}")

    return tools


def _resolve_env(env: dict[str, str]) -> dict[str, str]:
    """Resolve ${VAR} and ${VAR:-default} patterns from os.environ."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-(.*?))?\}")

    def replacer(m: re.Match) -> str:
        var_name, default = m.group(1), m.group(2)
        return os.environ.get(var_name, default or "")

    return {k: pattern.sub(replacer, v) for k, v in env.items()}
```

### 5.3 Chinese Embedding Retriever

```python
# src/petfish_bi_cli/retrieval/chinese_retriever.py
from __future__ import annotations
from typing import Any
import numpy as np
from petfishframework.core.contracts import Retriever
from petfishframework.core.types import Snippet


class ChineseEmbeddingRetriever(Retriever):
    """Embedding-based retriever with proper Chinese tokenization.

    Uses sentence-transformers with BGE-zh model for Chinese text.
    Falls back to jieba keyword matching if sentence-transformers unavailable.
    """

    def __init__(self, model_name: str = "BAAI/bge-base-zh-v1.5"):
        self._model_name = model_name
        self._model: Any = None
        self._docs: list[dict[str, Any]] = []

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except ImportError:
            import warnings
            warnings.warn(
                "sentence-transformers not installed. "
                "Install with: uv sync --extra rag. "
                "Falling back to jieba keyword matching."
            )
            self._model = "jieba_fallback"

    def add(self, content: str, metadata: dict[str, Any] | None = None):
        self._docs.append({"content": content, "metadata": metadata or {}})

    def build_index(self):
        """Pre-compute embeddings for all added documents."""
        self._ensure_model()
        if not self._docs or self._model == "jieba_fallback":
            return

        texts = [d["content"] for d in self._docs]
        self._embeddings = self._model.encode(texts, show_progress_bar=False)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        if not self._docs:
            return []

        self._ensure_model()

        if self._model == "jieba_fallback":
            return self._retrieve_jieba(query, top_k)

        return self._retrieve_embedding(query, top_k)

    def _retrieve_embedding(self, query: str, top_k: int) -> list[Snippet]:
        if not hasattr(self, "_embeddings") or self._embeddings is None:
            self.build_index()

        query_emb = self._model.encode([query])
        scores = (query_emb @ self._embeddings.T)[0]
        top_idx = np.argsort(scores)[-top_k:][::-1]

        return [
            Snippet(
                content=self._docs[i]["content"],
                source=self._docs[i]["metadata"].get("source", ""),
                score=float(scores[i]),
                metadata=self._docs[i]["metadata"],
            )
            for i in top_idx
            if scores[i] > 0.3
        ]

    def _retrieve_jieba(self, query: str, top_k: int) -> list[Snippet]:
        import jieba
        query_words = set(jieba.cut(query))

        scored: list[tuple[float, dict]] = []
        for doc in self._docs:
            doc_words = set(jieba.cut(doc["content"]))
            shared = len(query_words & doc_words)
            if shared == 0:
                continue
            score = shared / max(len(doc_words), 1)
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            Snippet(
                content=doc["content"],
                source=doc["metadata"].get("source", ""),
                score=score,
                metadata=doc["metadata"],
            )
            for score, doc in scored[:top_k]
        ]
```

### 5.4 RAG Loader

```python
# src/petfish_bi_cli/config/rag_loader.py
from __future__ import annotations
from pathlib import Path
from typing import Any

from petfishframework.core.contracts import Retriever
from petfishframework.retrieval import CRAGRetriever, MemoryRetriever


def build_retriever(
    config: dict,
    data_root: Path,
) -> Retriever | None:
    """Build CRAGRetriever from YAML config."""
    if not config.get("enabled", False):
        return None

    retrievers_cfg = config.get("retrievers", {})
    if not retrievers_cfg:
        return None

    base = _build_base_retriever(retrievers_cfg, data_root)
    return CRAGRetriever(base_retriever=base)


def _build_base_retriever(
    retrievers_cfg: dict[str, dict],
    data_root: Path,
) -> Retriever:
    has_embedding = any(
        cfg.get("index", {}).get("embedding_model")
        for cfg in retrievers_cfg.values()
    )

    if has_embedding:
        try:
            return _build_embedding_retriever(retrievers_cfg, data_root)
        except ImportError:
            pass

    return _build_keyword_retriever(retrievers_cfg, data_root)


def _build_embedding_retriever(retrievers_cfg, data_root) -> Retriever:
    from petfish_bi_cli.retrieval.chinese_retriever import ChineseEmbeddingRetriever

    merged = ChineseEmbeddingRetriever()
    for name, cfg in retrievers_cfg.items():
        model = cfg.get("index", {}).get("embedding_model", "BAAI/bge-base-zh-v1.5")
        merged = ChineseEmbeddingRetriever(model_name=model)
        _populate_retriever(merged, cfg, data_root)
        merged.build_index()

    return merged


def _build_keyword_retriever(retrievers_cfg, data_root) -> Retriever:
    base = MemoryRetriever()
    for name, cfg in retrievers_cfg.items():
        _populate_retriever(base, cfg, data_root)
    return base


def _populate_retriever(retriever, cfg: dict, data_root: Path):
    source = cfg.get("source", "")
    field = cfg.get("index", {}).get("field", "")
    if not source or not field:
        return

    docs = _load_source_data(source, field, data_root)
    for doc in docs:
        retriever.add(content=doc["content"], metadata={"source": source, **doc.get("metadata", {})})


def _load_source_data(source: str, field: str, data_root: Path) -> list[dict]:
    """Load data from ingestion adapters and extract the specified field."""
    from petfish_bi_cli.ingestion import load_source

    records = load_source(source, data_root)
    return [
        {"content": str(r.get(field, "")), "metadata": {"row": i}}
        for i, r in enumerate(records)
        if r.get(field)
    ]
```

### 5.5 Prompt Manager

```python
# src/petfish_bi_cli/config/prompt_manager.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import yaml


@dataclass
class PromptManager:
    """Git-native prompt management with hot-reload and dynamic few-shot."""

    system_prompt_file: Path
    few_shot_mode: str = "static"
    few_shot_pool_dir: Path = Path("configs/prompts/few_shot/")
    few_shot_k: int = 3
    few_shot_selection: str = "intent-first"
    _cache: dict[str, tuple[str, float]] = None

    def __post_init__(self):
        self.system_prompt_file = Path(self.system_prompt_file)
        self.few_shot_pool_dir = Path(self.few_shot_pool_dir)
        self._cache = {}

    def load_system_prompt(self) -> str:
        """Load system prompt with hot-reload (mtime check)."""
        content = self._load_cached(self.system_prompt_file)
        return content.replace("{current_date}", date.today().isoformat())

    def select_few_shot(self, query: str, intent: str | None = None) -> str:
        """Select few-shot examples based on mode and strategy."""
        if self.few_shot_mode == "off":
            return ""
        if self.few_shot_mode == "static":
            return self._load_static_examples()

        examples = self._load_pool()
        if not examples:
            return self._load_static_examples()

        selected = self._select(examples, query, intent)
        return "\n\n---\n\n".join(
            f"User: {ex['input']}\n{ex['output']}" for ex in selected
        )

    def _load_cached(self, path: Path) -> str:
        mtime = path.stat().st_mtime if path.exists() else 0.0
        cache_key = str(path)
        cached = self._cache.get(cache_key)
        if cached and cached[1] == mtime:
            return cached[0]
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        self._cache[cache_key] = (content, mtime)
        return content

    def _load_pool(self) -> list[dict[str, Any]]:
        """Load all YAML few-shot examples from pool directory."""
        if not self.few_shot_pool_dir.exists():
            return []

        examples: list[dict[str, Any]] = []
        for yml_file in self.few_shot_pool_dir.glob("*.yml"):
            data = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                examples.extend(data)
            elif isinstance(data, dict):
                examples.append(data)

        return examples

    def _load_static_examples(self) -> str:
        """Load from old-style .txt files."""
        old_dir = Path("src/petfish_bi_cli/prompts/few_shot/")
        if not old_dir.exists():
            return ""

        parts: list[str] = []
        for txt_file in old_dir.glob("*.txt"):
            parts.append(txt_file.read_text(encoding="utf-8"))
        return "\n\n---\n\n".join(parts)

    def _select(
        self,
        examples: list[dict[str, Any]],
        query: str,
        intent: str | None,
        k: int | None = None,
    ) -> list[dict[str, Any]]:
        k = k or self.few_shot_k

        if self.few_shot_selection == "intent-first" and intent:
            matched = [ex for ex in examples if ex.get("intent") == intent]
            if len(matched) >= k:
                return matched[:k]

        return examples[:k]
```

### 5.6 Framework Integration

```python
# src/petfish_bi_cli/framework.py (revised)
from __future__ import annotations
from pathlib import Path

from petfishframework import Agent, Budget
from petfishframework.models.fake import FakeModel

from petfish_bi_cli.config.settings import Settings, load_settings
from petfish_bi_cli.grounding.claims import ClaimsRegistry


def make_bi_agent(
    settings: Settings | None = None,
    registry: ClaimsRegistry | None = None,
) -> Agent:
    if settings is None:
        settings = load_settings()
    if registry is None:
        registry = ClaimsRegistry()

    # 1. Model
    model = _build_model(settings)

    # 2. Native tools
    explore = ExploreDataSourcesTool(semantic_dir=settings.semantic_dir)
    load = LoadDataTool(data_root=settings.data_root, registry=registry)
    analyze = AnalyzeTool(registry=registry)

    tools = [explore, load, analyze]

    # Sentiment tool (M5)
    if settings.analysis.get("sentiment"):
        from petfish_bi_cli.agent.tools.sentiment import SentimentAnalysisTool
        tools.append(SentimentAnalysisTool(
            config=settings.analysis.get("sentiment", {}),
            registry=registry,
            data_root=settings.data_root,
        ))

    # 3. MCP tools (M6-A)
    from petfish_bi_cli.config.mcp_loader import load_mcp_tools
    mcp_tools = load_mcp_tools({
        "auto_load": settings.mcp.auto_load,
        "servers": settings.mcp.servers,
    })
    tools.extend(mcp_tools)

    # 4. Retriever (M6-B)
    from petfish_bi_cli.config.rag_loader import build_retriever
    retriever = build_retriever(
        {"enabled": settings.retrieval.enabled, "retrievers": settings.retrieval.retrievers},
        settings.data_root,
    )

    # 5. Prompt manager (M6-C)
    from petfish_bi_cli.config.prompt_manager import PromptManager
    prompt_mgr = PromptManager(
        system_prompt_file=settings.prompts.system_prompt_file,
        few_shot_mode=settings.prompts.few_shot_mode,
        few_shot_pool_dir=settings.prompts.few_shot_pool_dir,
        few_shot_k=settings.prompts.few_shot_k,
        few_shot_selection=settings.prompts.few_shot_selection,
    )

    # 6. Strategy with prompt manager
    strategy = BIAgentStrategy(prompt_mgr=prompt_mgr)

    # 7. Budget
    budget = Budget(**settings.budget) if settings.budget else None

    return Agent(
        model=model,
        reasoning=strategy,
        tools=tuple(tools),
        retriever=retriever,
        budget=budget,
    )


def _build_model(settings: Settings):
    from petfish_bi_cli.config.model_factory import build_model
    return build_model(settings.model, settings.model_roles)
```

## 6. TDD Task Breakdown

| Task ID | Description | Test (RED) | Implementation (GREEN) |
|---|---|---|---|
| **Settings** | | | |
| M6-T001 | Settings loads from YAML | `test_settings_loads_yaml` → `settings.model.name == "gpt-4o"` | `settings.py: load_settings()` |
| M6-T002 | Settings defaults when no file | `test_settings_defaults` → FakeModel, no MCP | Same |
| M6-T003 | Settings applies env override | `test_settings_env_override` → `BI_CLI_MODEL` env | Same |
| **MCP** | | | |
| M6-T004 | MCP loader empty config | `test_mcp_loader_empty` → `[]` | `mcp_loader.py: load_mcp_tools()` |
| M6-T005 | MCP loader resolves env vars | `test_mcp_loader_env_resolve` → `${VAR}` expanded | `_resolve_env()` |
| M6-T006 | MCP loader connects stdio | `test_mcp_loader_stdio` → @integration, real MCP | `connect_stdio` integration |
| M6-T007 | MCP loader handles failure | `test_mcp_loader_failure` → warn, don't crash | Exception handling |
| **RAG** | | | |
| M6-T008 | Chinese retriever tokenizes CJK | `test_chinese_retriever_cjk` → 中文分词不丢失 | `chinese_retriever.py` |
| M6-T009 | Chinese retriever jieba fallback | `test_chinese_retriever_fallback` → 无 sentence-transformers 时用 jieba | Fallback logic |
| M6-T010 | RAG loader builds CRAG | `test_rag_loader_crag` → YAML → CRAGRetriever | `rag_loader.py` |
| M6-T011 | RAG loader populates from source | `test_rag_loader_populate` → CROCS 评论加载到 retriever | `_load_source_data()` |
| **Prompt** | | | |
| M6-T012 | Prompt manager loads system prompt | `test_prompt_mgr_system` → reads file with mtime | `prompt_manager.py` |
| M6-T013 | Prompt manager hot-reload | `test_prompt_mgr_hot_reload` → file change → new content | mtime cache |
| M6-T014 | Prompt manager dynamic few-shot | `test_prompt_mgr_dynamic` → intent=comparison → comparison example | `_select()` |
| M6-T015 | Prompt manager fallback to static | `test_prompt_mgr_fallback` → no YAML pool → static .txt | Fallback |
| **Integration** | | | |
| M6-T016 | make_bi_agent from full config | `test_make_agent_full` → all components injected | `framework.py` revised |
| M6-T017 | End-to-end with config | `test_e2e_config` → query via configured agent | Integration |

## 7. Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
rag = ["sentence-transformers>=2.7"]
prompt-test = ["promptfoo>=0.50"]
```

Install: `uv sync --extra rag` (for RAG), `uv sync --extra prompt-test` (for regression testing)

## 8. Migration Path

```
Phase 1: settings.py + model_factory.py  (M4 — model only)
Phase 2: mcp_loader.py                   (M6-A — MCP)
Phase 3: chinese_retriever.py + rag_loader.py  (M6-B — RAG)
Phase 4: prompt_manager.py               (M6-C — Prompts)
Phase 5: framework.py rewrite            (final integration)
```

Each phase is independently testable. No breaking changes to existing tests (all existing tests use `Settings()` defaults → FakeModel → no MCP → no RAG → static prompts).

## 9. ADR

### ADR-021: Single YAML Config File as Source of Truth

**Decision**: All configuration (model, MCP, RAG, prompts, analysis) lives in one `configs/bi_cli.yml` file, loaded by `load_settings()` into a frozen `Settings` dataclass.

**Rationale**: Single file = single mental model. Users edit one YAML, not 5 different config files. Frozen dataclass prevents runtime mutation. Env vars override YAML for secrets (API keys never in config files).

**Alternatives**: Multiple config files (model.yml, mcp.yml, prompts.yml) — rejected for cognitive overhead. TOML — rejected (YAML supports comments, better for Chinese text).

### ADR-022: MCP Auto-Loader via connect_stdio()

**Decision**: MCP servers declared in YAML are auto-loaded via `petfishframework.mcp.client.connect_stdio()`. The loader is fault-tolerant: if a server fails to connect, it warns and continues.

**Rationale**: Framework already has a complete MCP client. We just need a YAML → connect_stdio adapter. Fault tolerance is critical: one broken MCP server should not crash the Agent.

### ADR-023: ChineseEmbeddingRetriever with BGE-zh

**Decision**: Build a custom `ChineseEmbeddingRetriever` using `sentence-transformers` + `BAAI/bge-base-zh-v1.5`. Falls back to jieba keyword matching when sentence-transformers is not installed.

**Rationale**: `MemoryRetriever._tokenize()` uses `re.findall(r"[a-zA-Z0-9]+")` — it physically cannot tokenize Chinese characters. BGE-zh is the recommended Chinese embedding model (free, CPU-runnable, 1024-dim). Jieba fallback ensures the system works without heavy dependencies.

### ADR-024: Prompt Manager with mtime Hot-Reload

**Decision**: Prompt files are loaded with mtime-based caching. File modification is detected on next access, triggering reload without restart.

**Rationale**: During prompt development (iteration on grounding rules), restarting the CLI for every change is friction. mtime hot-reload enables "edit file → next query uses new prompt" workflow.

### ADR-025: Dynamic Few-Shot via Intent-First Selection

**Decision**: Few-shot examples are YAML files in a pool directory, each tagged with an `intent` field. At query time, examples matching the detected intent are selected first. Falls back to static .txt files if pool is empty.

**Rationale**: Static few-shot (current) always injects the same 2 examples regardless of query type. Intent-first selection injects relevant examples (comparison query → comparison examples), improving output quality. Fallback ensures backward compatibility.
