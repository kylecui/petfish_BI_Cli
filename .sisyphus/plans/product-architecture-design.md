# Product Architecture Design — petfish_BI_Cli Configuration-Driven Upgrade

## 0. Goal

Transform petfish_BI_Cli from a developer prototype (hardcoded tools, manual deployment) into a deliverable product (config-driven tools, one-command deploy, flexible output).

## 1. Current Architecture (what stays, what changes)

### STAYS (verified working, 343 tests)
- `BIApplication.execute()` — Agent orchestration + Grounding validation pipeline
- `ClaimsRegistry` + `validator.py` — Grounding layer
- `YamlPolicy` + `policy.yml` — Permission system
- `SIEMSink` + `PIIRedactingSink` — Audit pipeline
- `model_factory.py` — Model config + Vault integration
- `compliance/pii.py` — Centralized PII redaction
- `petfishframework` Agent/Session/Environment — Framework core

### CHANGES
- `semantic.py` → replaced by config-driven `SourceRegistry`
- `framework.py make_bi_agent()` → uses `ToolFactory` instead of hardcoded tools
- `renderers/markdown.py` → generalized to `rendering/renderer.py` with config templates
- `agent/tools/` → restructured: builtin analytical tools + config-generated tools
- `rag/` → config-driven retriever construction
- `main.py` → add `health` + `web` commands (new CLI subcommands for deployment verification and web server launch)

## 2. Config Schema (bi_cli.yml extended)

```yaml
# === EXISTING (unchanged) ===
model: { provider, name, api_key, base_url, temperature, max_tokens }
budget: { max_tokens_per_session, max_cost_usd, max_steps }
vault: { enabled, url, token, api_key_path }
# data.root stays as the project-relative root for resolving source paths.
# data.semantic_dir is DEPRECATED — superseded by `sources:` section.
#   If `sources:` is absent, the loader falls back to data.semantic_dir
#   (default: references/semantic) for backward compat with semantic/*.yml.
data:
  root: references
  semantic_dir: references/semantic  # deprecated, kept for backward compat fallback

# === NEW: Data Sources ===
sources:
  jd_products:
    type: json                          # json | csv | jsonl
    path: references/jd/products.json   # relative to project root
    description: "京东商品列表"
    schema:
      json_path: "raw_data.search_results[]"   # dot-path into JSON
      # OR for CSV: columns auto-detected from header
    metrics:
      - name: avg_price
        column: calculatedFinalPrice
        aggregation: avg
        unit: CNY
      - name: product_count
        aggregation: count
    entities:
      - name: brand
        values: ["CROCS"]
        source_column: skuName

# === NEW: RAG ===
rag:
  enabled: false
  documents:
    - path: docs/brand-guide.md
    - path: references/spec.pdf
      type: pdf
  retriever: crag                       # simple | crag
  chunk_size: 500
  top_k: 5

# === NEW: BI Scripts ===
scripts:
  sales_report:
    command: "python scripts/sales_report.py"
    description: "生成销售报表"
    input_schema:
      type: object
      properties:
        start_date: { type: string }
        end_date: { type: string }
      required: [start_date, end_date]
    output_format: json                 # json | text
    timeout_s: 30
    risk_level: medium                  # low | medium | high
    capabilities: ["data:read"]

# === NEW: Output Templates ===
templates:
  default:
    json: templates/report.json.j2       # JSON output template
    markdown: templates/report.md.j2     # rich content template
    html: templates/report.html.j2       # web rendering
```

### Config Validation Rules
- `sources.*.type` must be one of: json, csv, jsonl
- `sources.*.path` must exist at startup (fail fast)
- `sources.*.metrics` optional — if omitted, auto-detect numeric columns
- `scripts.*.command` must be executable (check at startup)
- `scripts.*.timeout_s` default 30, max 300
- `templates.*` paths must exist if specified
- Unknown top-level keys → warning (forward compat)

## 3. Tool Dynamic Generation Architecture

### 3.1 SourceRegistry (replaces semantic.py)

```python
@dataclass(frozen=True)
class SourceDeclaration:
    source_id: str
    type: str               # json | csv | jsonl
    path: Path
    description: str
    schema: dict            # json_path, columns, etc.
    metrics: tuple[MetricSpec, ...]
    entities: tuple[EntitySpec, ...]

class SourceRegistry:
    """Loads source declarations from config, provides lookup."""
    def __init__(self, config: dict): ...
    def get(self, source_id: str) -> SourceDeclaration: ...
    def all_sources(self) -> dict[str, SourceDeclaration]: ...
    def to_metadata(self) -> dict[str, SourceMetadata]:
        """Convert to legacy SourceMetadata for backward compat."""
```

### 3.2 ToolFactory

```python
class ToolFactory:
    """Builds tool instances from config-driven declarations."""

    def build_all(
        self,
        sources: SourceRegistry,
        scripts: dict[str, ScriptConfig],
        registry: ClaimsRegistry,
        data_root: Path,
    ) -> tuple[Tool, ...]:
        tools = []
        tools.append(ExploreDataSourcesTool(sources))    # dynamic
        tools.append(LoadDataTool(sources, registry))     # multi-source
        # Built-in analytical tools (work on any source)
        tools.append(SentimentAnalysisTool(data_root, registry))
        tools.append(TrendTool(data_root, registry))
        tools.append(CrossSourceComparisonTool(data_root, registry))
        tools.append(CrossTimeTool(data_root, registry))
        # Config-generated script tools
        for script_id, cfg in scripts.items():
            tools.append(ScriptTool(script_id, cfg, registry))
        return tuple(tools)
```

### 3.3 Key changes to existing tools

**ExploreDataSourcesTool**: Constructor changes from `semantic_dir: Path` → `sources: SourceRegistry`. Returns source summaries from config, not from `references/semantic/*.yml` files.

**LoadDataTool**: Constructor changes from `data_root: Path, registry` → `sources: SourceRegistry, registry`. `execute()` looks up `source_id` in registry, uses the declared schema (json_path, columns, metrics) to parse data. Metric computation (avg, min, max, count) is generic — driven by `MetricSpec.aggregation`.

**SentimentAnalysisTool, TrendTool, CrossSourceComparisonTool, CrossTimeTool**: These work on specific data structures (comment text, time-series prices). They need source-type awareness:
- Sentiment only works on sources with text/comment columns
- Trend only works on sources with timestamp + price columns
- Cross-source/cross-time work on price data

Design: These tools check source compatibility at execution time (return ToolResult(error) for incompatible sources). They do NOT hardcode source IDs.

### 3.4 Agent system prompt

The system prompt (`system_prompt.md`) currently has hardcoded source descriptions. With config-driven sources, the prompt is **generated dynamically** at agent creation time:

```python
# In BIAgentStrategy._system_prompt():
source_descriptions = "\n".join(
    f"- {s.source_id}: {s.description} (metrics: {', '.join(m.name for m in s.metrics)})"
    for s in sources.all_sources().values()
)
prompt = base_prompt.replace("{sources}", source_descriptions)
```

## 4. BI Script Execution Model

### 4.1 ScriptTool

```python
class ScriptTool:
    """Wraps a customer BI script as an Agent-callable Tool."""

    def __init__(self, script_id: str, config: ScriptConfig, registry: ClaimsRegistry):
        self.name = f"run_{script_id}"
        self.description = config.description
        self.input_schema = config.input_schema
        self.risk_level = config.risk_level_enum  # from string → RiskLevel
        self.capabilities = tuple(config.capabilities)
        self.side_effect = True     # scripts mutate state by default
        self.idempotent = False     # scripts may not be deterministic
        self.external_egress = config.network_access
        self._command = config.command
        self._timeout = config.timeout_s
        self._output_format = config.output_format
        self._registry = registry
        self._claim_counter = 0

    def execute(self, args: dict) -> ToolResult:
        result = self._run_subprocess(args)
        if result.returncode != 0:
            return ToolResult(error=f"Script exited {result.returncode}: {result.stderr}")
        return self._parse_and_register(result.stdout)

    def _run_subprocess(self, args: dict) -> subprocess.CompletedProcess:
        # Inject args as JSON via stdin
        return subprocess.run(
            self._command, shell=True, input=json.dumps(args),
            capture_output=True, text=True, timeout=self._timeout,
        )

    def _parse_and_register(self, output: str) -> ToolResult:
        if self._output_format == "json":
            data = json.loads(output)
            claims = self._register_json_claims(data)
            return ToolResult(value={"output": data, "claims": claims})
        return ToolResult(value={"output": output})
```

### 4.2 Claim Registration from Script Output

Script output (JSON) is scanned for numeric values. Each top-level numeric field or numeric field in a list of dicts becomes a claim:

```python
def _register_json_claims(self, data: dict | list) -> list[dict]:
    claims = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                claim = self._make_claim(
                    metric=f"{self.name}.{key}",
                    value=value,
                    source=self.name,
                    computation="script_output",
                )
                claims.append({"id": claim.id, "metric": claim.metric, "value": claim.value})
    return claims
```

### 4.3 Safety Boundaries

- **YamlPolicy**: Scripts have `side_effect=True` by default. The default policy DENIES tools with `side_effect=True`. Customers must add an explicit allow rule for each script they want the agent to use.
- **Timeout**: Enforced via `subprocess.run(timeout=...)`. Default 30s, max 300s.
- **No credential injection**: Scripts do NOT receive credential tokens. They run with process-level permissions only.
- **Output size**: Script stdout limited to 1MB (truncate + warn).

## 5. Output Template System

### 5.1 Rendering Pipeline

```
BIReport(answer, data) → validate_report() → BIReport(validated)
→ render_template(report, claims) → BIReport(rich_content=rendered)
```

Grounding validation runs on the Agent's raw answer BEFORE rendering. Templates are presentation-only — they format data that's already validated.

### 5.2 Template Context

Templates receive:
- `report.answer` — Agent's natural language answer (PII-redacted)
- `report.data` — Structured findings dict
- `report.session_id` — For citation
- `claims` — ClaimsLedger (for rendering claim references)
- `sources` — List of source IDs used (for provenance footer)

### 5.3 Template Configuration

Templates are configured in `bi_cli.yml`:
```yaml
templates:
  default:
    json: templates/report.json.j2
    markdown: templates/report.md.j2
```

The `rendering/renderer.py` module loads templates from the configured paths:
```python
class ReportRenderer:
    def __init__(self, template_config: dict):
        self._env = Environment(loader=FileSystemLoader("."))  # project root
        self._templates = template_config

    def render_json(self, report, claims) -> str: ...
    def render_markdown(self, report, claims) -> str: ...
    def render_html(self, report, claims) -> str: ...
```

### 5.4 Grounding Interaction

- Templates MUST NOT compute new numbers from claim values
- If a template displays a number, it uses the exact value from `report.data.findings[i].value`
- The `validate_report()` pass runs on the raw answer, NOT the rendered template
- Rationale: templates are display formatting, not analytical computation

## 6. Directory Structure (proposed)

```
src/petfish_bi_cli/
├── agent/
│   ├── tools/
│   │   ├── builtin/        # sentiment, trend, cross_source, cross_time
│   │   ├── data_source.py  # LoadDataTool (config-driven)
│   │   ├── explore.py      # ExploreDataSourcesTool (config-driven)
│   │   └── script.py       # ScriptTool (customer BI scripts)
│   ├── strategy.py
│   ├── tool_factory.py     # NEW: config → tool instances
│   └── prompts/
├── config/
│   ├── settings.py         # extended: sources, rag, scripts, templates
│   ├── model_factory.py
│   └── source_registry.py  # NEW: replaces semantic.py
├── compliance/
├── domain.py
├── application.py
├── framework.py            # make_bi_agent uses ToolFactory
├── grounding/
├── observability/
├── rendering/
│   ├── renderer.py         # generalized from renderers/markdown.py
│   └── templates/          # default templates (overridable by config)
├── rag/
└── web/
```

## 7. Deployment

### 7.1 install.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== petfish BI CLI Setup ==="

# Check Python
python3 --version || { echo "Python 3 required"; exit 1; }

# Check uv
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Install dependencies
uv sync --extra web --extra openai

# Initialize configs from templates
if [ ! -f configs/bi_cli.yml ]; then
    cp configs/bi_cli.example.yml configs/bi_cli.yml
    echo "Created configs/bi_cli.yml from template"
fi

# Verify
uv run petfish-bi health || { echo "Setup verification failed"; exit 1; }
echo "=== Setup complete. Run: petfish-bi --help ==="
```

### 7.2 Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --extra web --extra openai --no-dev
EXPOSE 8000
CMD ["uv", "run", "petfish-bi", "web", "--host", "0.0.0.0"]
```

### 7.3 AGENT Deployment Guide

A `DEPLOY.md` file that an AI agent can execute step-by-step:
1. Clone repo
2. Run install.sh
3. Edit configs/bi_cli.yml (set model provider + API key)
4. Add data sources to references/
5. Declare sources in bi_cli.yml
6. Run `petfish-bi health` to verify
7. Start web server or use CLI

## 8. Sprint Breakdown

### S3: Config-Driven Data Sources (foundation)
**Input**: bi_cli.yml with `sources` section
**Output**: Agent uses config-declared sources, not hardcoded references/semantic/*.yml
**Files**: source_registry.py, tool_factory.py, load_data.py rewrite, explore.py rewrite
**Verification**: `petfish-bi ask "列出所有数据源"` returns config-declared sources; existing golden tests pass with equivalent config

### S4: BI Script Integration
**Input**: bi_cli.yml with `scripts` section
**Output**: Agent can call customer scripts as tools
**Files**: script.py (ScriptTool), tool_factory.py extension
**Verification**: Declare a test script in config → agent calls it → claim registered → grounded in answer

### S5: Output Template System
**Input**: bi_cli.yml with `templates` section
**Output**: Configurable JSON/Markdown/HTML rendering
**Files**: rendering/renderer.py, template files
**Verification**: Custom template renders report with claim citations; grounding validation unaffected

### S6: One-Command Deployment
**Prerequisite task**: Implement `petfish-bi health` and `petfish-bi web` CLI commands in `main.py` — health checks config loadability, data root exists, model adapter constructible (exits 0/1); web wraps `uvicorn petfish_bi_cli.web:app` with configurable host/port (used by Dockerfile CMD).
**Input**: install.sh + Dockerfile + DEPLOY.md + health command
**Output**: One-command setup on clean machine
**Files**: main.py (health command), install.sh, Dockerfile, docker-compose.yml, DEPLOY.md, configs/bi_cli.example.yml
**Verification**: Fresh clone → install.sh → `petfish-bi health` exits 0

### S7: Config Wizard (optional, lower priority)
**Input**: `petfish-bi config init` command
**Output**: Interactive CLI wizard that generates bi_cli.yml
**Files**: cli/config_command.py
**Verification**: Wizard produces valid config → health check passes

## 9. Migration Strategy

The upgrade is **backward compatible**:
- If `sources` section is absent in bi_cli.yml, fall back to reading `references/semantic/*.yml` (via the existing `data.semantic_dir` config field, default `references/semantic`). This preserves the current `semantic.py` → `load_all_metadata()` code path unchanged.
- `data.root` STAYS as the project-relative root for resolving all source paths. The new `sources.*.path` values are resolved relative to `data.root`.
- `data.semantic_dir` is DEPRECATED but retained. When `sources:` is present, it takes precedence over `data.semantic_dir`. When both exist, `sources:` wins.
- If `scripts` section is absent, no script tools created (current behavior)
- If `templates` section is absent, use default templates from `rendering/templates/`
- Existing 343 tests pass without modification (config is additive; `sources:` absent = current behavior)

## 10. Risks

| Risk | Mitigation |
|---|---|
| LoadDataTool rewrite breaks existing golden tests | Keep SourceMetadata backward compat; auto-convert config → SourceMetadata |
| ScriptTool subprocess injection | shell=True but command from trusted config (not user input); YamlPolicy denies by default |
| Template rendering loses claim_ids | Templates are display-only; claims tracked separately in report.data |
| Config validation too strict → customer can't start | Distinguish ERROR (must fix) vs WARNING (degrade gracefully) |
| Source auto-detection wrong metrics | Always allow manual override in config; auto-detect is convenience, not source of truth |

## 11. Task Dependency Graph

```
S3-T1 (SourceRegistry dataclass + parser)
  │
  ├──> S3-T2 (LoadDataTool rewrite: uses SourceRegistry)
  │
  ├──> S3-T3 (ExploreDataSourcesTool rewrite: uses SourceRegistry)
  │
  └──> S3-T4 (ToolFactory: orchestrates all tool creation)
         │
         └──> S3-T5 (framework.py: make_bi_agent uses ToolFactory)
                │
                ├──> S4-T1 (ScriptTool)  ── [parallel with S5]
                │      └──> S4-T2 (ToolFactory extension: add ScriptTool)
                │
                ├──> S5-T1 (ReportRenderer)  ── [parallel with S4]
                │      └──> S5-T2 (application.py: wire renderer into execute())
                │
                └──> S6-T1 (health command) ── [parallel with S4/S5]
                       └──> S6-T2 (install.sh + Dockerfile + DEPLOY.md)
                              └──> S6-T3 (configs/bi_cli.example.yml)
```

**Critical path**: S3-T1 → S3-T4 → S3-T5 → S6-T2 (deployment depends on everything else).

## 12. Parallel Execution Graph

```
WAVE 1 (sequential, foundation):
  S3-T1: SourceRegistry dataclass + config parsing
  S3-T2: LoadDataTool rewrite
  S3-T3: ExploreDataSourcesTool rewrite
  S3-T4: ToolFactory
  S3-T5: framework.py wiring

WAVE 2 (parallel, independent features):
  ┌─ S4-T1: ScriptTool
  ├─ S5-T1: ReportRenderer
  └─ S6-T1: health command

WAVE 3 (integration):
  ┌─ S4-T2: ToolFactory + ScriptTool wiring
  ├─ S5-T2: application.py + renderer wiring
  └─ S6-T2: install.sh + Dockerfile + DEPLOY.md

WAVE 4 (finalization):
  └─ S6-T3: configs/bi_cli.example.yml + full integration test
```

## 13. TDD Task Breakdown

Each task follows: **write failing test → implement → test passes → commit**.

### S3-T1: SourceRegistry
- **Test first**: `tests/test_config/test_source_registry.py`
  - `test_parses_sources_from_config_dict()` — YAML config → SourceDeclaration objects
  - `test_falls_back_to_semantic_dir_when_no_sources()` — backward compat
  - `test_to_metadata_converts_to_legacy_SourceMetadata()` — backward compat
  - `test_invalid_source_type_raises()` — validation
- **Implement**: `src/petfish_bi_cli/config/source_registry.py`
- **Commit**: `feat(config): SourceRegistry — config-driven source declarations`

### S3-T2: LoadDataTool rewrite
- **Test first**: `tests/test_tools/test_load_config.py`
  - `test_load_data_uses_source_registry()` — loads from SourceDeclaration
  - `test_metric_computation_from_metric_spec()` — avg/min/max/count generic
  - `test_existing_golden_data_still_loads()` — backward compat
- **Implement**: rewrite `src/petfish_bi_cli/agent/tools/load.py`
- **Commit**: `feat(tools): LoadDataTool uses SourceRegistry`

### S3-T3: ExploreDataSourcesTool rewrite
- **Test first**: `tests/test_tools/test_explore_config.py`
  - `test_explore_returns_config_sources()`
  - `test_explore_single_source_from_config()`
- **Implement**: rewrite `src/petfish_bi_cli/agent/tools/explore.py`
- **Commit**: `feat(tools): ExploreDataSourcesTool uses SourceRegistry`

### S3-T4: ToolFactory
- **Test first**: `tests/test_agent/test_tool_factory.py`
  - `test_build_all_creates_all_builtin_tools()`
  - `test_build_all_creates_script_tools_from_config()`
  - `test_build_all_with_no_sources_falls_back()`
- **Implement**: `src/petfish_bi_cli/agent/tool_factory.py`
- **Commit**: `feat(agent): ToolFactory — config-driven tool creation`

### S3-T5: framework.py wiring
- **Test first**: `tests/test_framework.py` (extend existing)
  - `test_make_bi_agent_uses_tool_factory()`
  - `test_make_bi_agent_with_sources_config()`
  - `test_make_bi_agent_without_sources_falls_back()`
- **Implement**: update `src/petfish_bi_cli/framework.py`
- **Commit**: `feat(framework): make_bi_agent uses ToolFactory + SourceRegistry`

### S4-T1: ScriptTool
- **Test first**: `tests/test_tools/test_script.py`
  - `test_executes_command_and_parses_json_output()`
  - `test_registers_claims_from_numeric_fields()`
  - `test_timeout_returns_error()`
  - `test_nonzero_exit_returns_error()`
  - `test_side_effect_true_by_default()`
- **Implement**: `src/petfish_bi_cli/agent/tools/script.py`
- **Commit**: `feat(tools): ScriptTool — customer BI script wrapper`

### S4-T2: ToolFactory + ScriptTool wiring
- **Test first**: extend `tests/test_agent/test_tool_factory.py`
  - `test_build_all_includes_script_tools()`
- **Implement**: extend `tool_factory.py` build_all()
- **Commit**: `feat(agent): ToolFactory registers ScriptTool from config`

### S5-T1: ReportRenderer
- **Test first**: `tests/test_rendering/test_renderer.py`
  - `test_render_json_uses_configured_template()`
  - `test_render_markdown_with_claim_citations()`
  - `test_render_html_basic()`
  - `test_grounding_validation_unaffected_by_rendering()`
- **Implement**: `src/petfish_bi_cli/rendering/renderer.py`
- **Commit**: `feat(rendering): ReportRenderer with configurable templates`

### S5-T2: application.py wiring
- **Test first**: `tests/test_bi_application.py` (extend)
  - `test_execute_renders_rich_content_when_template_configured()`
  - `test_execute_without_templates_works()`
- **Implement**: extend `application.py` execute()
- **Commit**: `feat(app): wire ReportRenderer into BIApplication.execute()`

### S6-T1: health + web commands
- **Test first**: `tests/test_cli/test_health.py` + `tests/test_cli/test_web_cmd.py`
  - `test_health_exits_0_when_config_valid()`
  - `test_health_exits_1_when_data_root_missing()`
  - `test_health_reports_model_status()`
  - `test_web_command_starts_uvicorn()` — uses TestClient to verify FastAPI app mounts
- **Implement**: add `health` and `web` commands to `src/petfish_bi_cli/main.py`
  - `health`: checks config loadability, data root exists, model adapter constructible. Exits 0/1.
  - `web`: wraps `uvicorn petfish_bi_cli.web:app` with configurable host/port. This unifies CLI access to the web server (Dockerfile uses `petfish-bi web`).
- **Commit**: `feat(cli): petfish-bi health + web commands`

### S6-T2: install.sh + Docker + DEPLOY.md
- **Test first**: `tests/test_deployment/test_install.sh` (shellcheck + dry run)
  - `test_install_creates_config_from_example()`
  - `test_install_runs_uv_sync()`
  - `test_install_verifies_health()`
- **Implement**: `install.sh`, `Dockerfile`, `docker-compose.yml`, `DEPLOY.md`
- **Commit**: `feat(deploy): one-command deployment via install.sh + Docker`

### S6-T3: configs/bi_cli.example.yml + integration
- **Test first**: `tests/test_deployment/test_example_config.py`
  - `test_example_config_loads_without_error()`
  - `test_example_config_has_documented_sections()`
- **Implement**: `configs/bi_cli.example.yml` (fully commented template)
- **Commit**: `feat(config): bi_cli.example.yml with all documented sections`

## 14. Atomic Commit Strategy

Each commit is atomic, independently testable, and follows conventional commit format.

| Commit # | Message | Files | Test Gate |
|---|---|---|---|
| 1 | `feat(config): SourceRegistry — config-driven source declarations` | source_registry.py, test_source_registry.py | new tests pass |
| 2 | `feat(tools): LoadDataTool uses SourceRegistry` | load.py, test_load_config.py | golden tests pass |
| 3 | `feat(tools): ExploreDataSourcesTool uses SourceRegistry` | explore.py, test_explore_config.py | new tests pass |
| 4 | `feat(agent): ToolFactory — config-driven tool creation` | tool_factory.py, test_tool_factory.py | new tests pass |
| 5 | `feat(framework): make_bi_agent uses ToolFactory + SourceRegistry` | framework.py, test_framework.py | full suite passes |
| 6 | `feat(tools): ScriptTool — customer BI script wrapper` | script.py, test_script.py | new tests pass |
| 7 | `feat(agent): ToolFactory registers ScriptTool from config` | tool_factory.py | existing tests pass |
| 8 | `feat(rendering): ReportRenderer with configurable templates` | rendering/renderer.py, test_renderer.py | new tests pass |
| 9 | `feat(app): wire ReportRenderer into BIApplication.execute()` | application.py | bi_application tests pass |
| 10 | `feat(cli): petfish-bi health + web commands` | main.py, test_health.py, test_web_cmd.py | new tests pass |
| 11 | `feat(deploy): one-command deployment via install.sh + Docker` | install.sh, Dockerfile, docker-compose.yml, DEPLOY.md | install dry-run passes |
| 12 | `feat(config): bi_cli.example.yml with all documented sections` | configs/bi_cli.example.yml | example config loads |

**Rule**: Never commit if any test fails. Run `uv run pytest -q` before every commit.

## 15. Category + Skills Recommendations

| Task | Category | Skills |
|---|---|---|
| S3-T1 SourceRegistry | `deep` | [] |
| S3-T2 LoadDataTool | `deep` | [] |
| S3-T3 ExploreTool | `quick` | [] |
| S3-T4 ToolFactory | `deep` | [] |
| S3-T5 framework wiring | `deep` | [] |
| S4-T1 ScriptTool | `deep` | [] |
| S4-T2 ToolFactory ext | `quick` | [] |
| S5-T1 ReportRenderer | `deep` | [] |
| S5-T2 app wiring | `quick` | [] |
| S6-T1 health cmd | `quick` | [] |
| S6-T2 deploy scripts | `unspecified-low` | [] |
| S6-T3 example config | `quick` | [] |
