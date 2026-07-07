# Backlog — TDD Task Breakdown

> 架构依据：`docs/architecture.md`（ADR-004~010）+ `docs/bi-domain-intelligence.md`（ADR-011~015）
> 方法论：Outside-in TDD（ADR-009）— 每个 TASK 从失败测试开始（Red → Green → Refactor）
> 执行顺序严格自上而下；跨 milestone 的 TASK 可并行（如 M1 的 4 个 ingestion adapter）

---

## M-1 — Domain Intelligence（BI 领域智能层）

**目标**：构建 Semantic Layer + Grounding Tools + BIAgentStrategy + OutputValidator。M0 前必须完成，否则 BIApplication 无 grounding 约束。

**依据**：`docs/bi-domain-intelligence.md`

### Semantic Layer（ADR-014）

- [ ] **T101** `references/semantic/entities.yml` — 跨源实体注册表（brand/platform/metric 别名归一化）
  - RED: `tests/test_semantic/test_entities_load` — YAML 解析正确
  - GREEN: 按文档 §3.5 结构填充 CROCS/HUGO_BOSS/ADIDAS 等 brand、JD/TMALL platform、price/comment_count metric

- [ ] **T102** `references/semantic/crocs_xiaohongshu.yml` — CROCS CSV 元数据（舆情/UGC）
  - RED: `tests/test_semantic/test_crocs_meta` — schema columns 与实际 CSV 匹配
  - GREEN: 按文档 §3.2 填充（搜索关键词/笔记标题/评论内容/评论时间等 12 列）

- [ ] **T103** `references/semantic/jd_products.yml` — JD JSON 元数据
  - RED: `tests/test_semantic/test_jd_meta` — json_path + columns 匹配实际 JSON
  - GREEN: 按文档 §3.3（raw_data.search_results[]，skuId/originalPrice/calculatedFinalPrice）

- [ ] **T104** `references/semantic/tmall_products.yml` + `rose_10brands.yml` — TMALL/ROSE JSONL 元数据
  - RED: `tests/test_semantic/test_jsonl_meta` — jsonl_structure.items_path 匹配
  - GREEN: 按文档 §3.4（extracted_items[]，itemId/price/title/shop）

### Grounding Tools（ADR-011/012）

- [ ] **T105** `grounding/claims.py` — `Claim` + `ClaimsLedger` dataclass
  - RED: `tests/test_grounding/test_claims.py::test_claim_is_frozen`
  - GREEN: `@dataclass(frozen=True)` with id/metric/value/source/source_rows/computation（⚠️ 非参数化泛型，ADR-009 框架限制）

- [ ] **T106** `agent/tools/explore.py` — `explore_data_sources` Tool
  - RED: `tests/test_tools/test_explore.py::test_explore_returns_source_list`
  - GREEN: 读 `references/semantic/*.yml`，返回数据源摘要（source_id + description + 可用 metrics）
  - 实现 `Tool` Protocol（name/description/input_schema/risk_level/capabilities/execute）

- [ ] **T107** `agent/tools/load.py` — `load_data` Tool（返回 ClaimsLedger，不返回 raw data）
  - RED: `tests/test_tools/test_load.py::test_load_jd_returns_claims`
  - GREEN: 按 source 参数分发到 ingestion adapter，返回 `ClaimsLedger`（claims + metadata，ADR-012）
  - 依赖 M1 ingestion adapter；M-1 阶段先用 fixture/stub

- [ ] **T108** `agent/tools/analyze.py` — `analyze` Tool（确定性计算引擎）
  - RED: `tests/test_tools/test_analyze.py::test_compare_two_claims`
  - GREEN: 接收 claim IDs + operation（compare/aggregate/rank），返回新 Claim（带 computed value）

### BIAgentStrategy（ADR-015）

- [ ] **T109** `agent/strategy.py` — `BIAgentStrategy(ReAct)` 子类
  - RED: `tests/test_agent/test_strategy.py::test_system_prompt_contains_grounding_rules`
  - GREEN: override `_system_prompt()`，注入文档 §5.2 的 7 段式 prompt + 语义层摘要
  - 验证：prompt 含"ONLY use data from Tools"、claims 引用规则、输出格式

- [ ] **T110** `prompts/system_prompt.md` + `prompts/few_shot/*.txt` — Prompt 文件
  - RED: 文件存在且包含必要段（Role/Grounding Rules/Tool Use/Output Format）
  - GREEN: 按文档 §5.2/§5.3 写入；few_shot 按 4 种意图各一个示例（comparison/lookup/sentiment/ranking）

### OutputValidator（ADR-013）

- [ ] **T111** `grounding/validator.py` — `OutputValidator`
  - RED: `tests/test_grounding/test_validator.py::test_unverified_number_rejected`
  - GREEN: 实现 `validate(report, claims) → ValidationResult`
  - 校验 1：每个 finding.value 必须匹配某 claim.value
  - 校验 2：answer 文本中数字必须出现在某 claim value 中（regex 提取 + 匹配）

**M-1 验收**：`uv run pytest tests/test_grounding tests/test_tools tests/test_semantic` 通过；ClaimsLedger + OutputValidator + BIAgentStrategy 可被 M0 的 BIApplication 使用。

---

## M0 — Core Wiring（BIApplication 端到端 FakeModel + Grounding）

**目标**：跑通 `BIApplication.execute(BIQuery) → BIReport`，含 grounding 校验。

**变更**：M0 现在使用 `BIAgentStrategy`（非默认 ReAct）+ `OutputValidator`（M-1 产出）。

- [ ] **T001** `domain.py` — 定义 `BIQuery`/`BIReport` dataclass（`@dataclass(frozen=True)`）
  - ⚠️ **框架限制**：字段类型必须用非参数化泛型（`dict` 而非 `dict[str, Any]`、`tuple` 而非 `tuple[str, ...]`）。原因：`run_structured._coerce_value()` line 176 调用 `isinstance(value, dict[str, Any])` 会抛 TypeError。详见 `docs/architecture.md` §3.2。
  - RED: `tests/test_domain.py::test_biquery_is_frozen`
  - GREEN: 实现 dataclass（`data: dict`、`metadata: dict`、`usage: dict` 均非参数化）
  - REFACTOR: 提取公共字段

- [ ] **T002** `framework.py` — Agent 构建器 + `make_bi_agent(model, tools)` 工厂（ADR-008 适配层）
  - RED: `tests/test_framework.py::test_make_bi_agent_returns_frozen_agent`
  - GREEN: 封装 `Agent(model=..., reasoning=ReAct(), tools=...)`
  - 验证：`isinstance(agent, Agent)` 且 `agent.tools == tools`

- [ ] **T003** `tools/csv_loader.py` — `CSVLoaderTool`（最小版：读 CSV → list[dict]）
  - RED: `tests/test_tools/test_csv_loader.py::test_load_crocs_sample_returns_records`
  - GREEN: 实现 `Tool` Protocol（`name`/`description`/`input_schema`/`risk_level`/`capabilities`/`execute()`）
  - 构造时注入 `data_root: Path`
  - 用 `references/` 下真实 CROCS CSV 做 fixture

- [ ] **T004** `application.py` — `BIApplication.execute(BIQuery) → BIReport`（同步路径 + grounding）
  - RED: `tests/test_bi_application.py::test_execute_returns_correct_report`（**架构验证测试 — ADR-009 第一个测试**）
  - 用 `FakeModel.script_tool_then_answer(tool_name="load_csv", tool_args={...}, final_answer=<合法JSON>)` 配置 Agent
  - ⚠️ **FakeModel API**：参数名是 `tool_name`（非 `tool_call`）、`final_answer`（非 `answer_template`）。详见 `docs/architecture.md` §5.1。
  - 断言 `report.status == "ok"` 且 `report.data["findings"]` 中每个 finding 有 `claim_id`
  - GREEN: 实现 `BIApplication.__init__(agent, data_root)` + `execute(query)`
  - **内部流程**：`agent.run_structured(Task(...), BIReport)` → 解包 `StructuredResult.data` → **`OutputValidator.validate(report, claims_ledger)`**（M-1 T111）→ 通过返回 report；不通过返回 `BIReport(status="validation_failed")`
  - Agent 用 `BIAgentStrategy()`（M-1 T109），非默认 `ReAct()`

- [ ] **T005** `application.py` — `BudgetExceeded` 错误处理
  - RED: `test_execute_budget_exceeded_returns_error_report`（FakeModel 配置超长输出触发 budget）
  - GREEN: try/except `BudgetExceeded` → 返回 `BIReport(status="budget_exceeded")`

- [ ] **T006** `application.py` — `session_id` 暴露 + `get_session(session_id)` resume 支持
  - RED: `test_execute_returns_session_id` + `test_get_session_returns_same_session`
  - GREEN: `BIApplication` 内部记录 `session_id → Session` 映射

**M0 验收**：`uv run pytest tests/test_bi_application.py` 通过；FakeModel + 真实 CROCS CSV 数据流端到端跑通。

---

## M1 — Ingestion Adapters（每数据源一套，ADR-010）

**目标**：4 个数据源的 ingestion 全部完成，各有独立测试套件。可并行。
**⚠️ 数据真相**：CROCS CSV 是小红书UGC评论（非销售记录）；TMALL/ROSE 是 JSONL（非标准JSON）。

- [ ] **T010** `ingestion/crocs.py` — CROCS 小红书 CSV → `CommentRecord[]`（舆情数据）
  - RED: `tests/test_ingestion/test_crocs.py`（正常评论 + 缺字段 + 编码异常 + "无"占位符）
  - GREEN: 解析 `references/CROCS_原始数据_*.csv`（搜索关键词/笔记标题/评论内容/评论时间等 12 列）
  - 输出：`CommentRecord(note_title, commenter, comment_text, comment_time, search_keyword, ...)`
  - ⚠️ "无"在评论人/评论内容/评论时间字段中表示空值（非字符串"无"）

- [ ] **T011** `ingestion/jd.py` — JD JSON → `ProductRecord[]`（标准JSON，4条商品）
  - RED: `tests/test_ingestion/test_jd.py`（正常商品 + coupons 嵌套结构）
  - GREEN: 解析 `references/JD_CROCS_Raw_Memory_Dump.json`（raw_data.search_results[]）
  - 输出：`ProductRecord(sku_id, sku_name, shop_name, original_price, final_price, is_jd_self)`

- [ ] **T012** `ingestion/tmall.py` — TMALL **JSONL** → `ProductRecord[]`（23 dump / 1275 商品）
  - RED: `tests/test_ingestion/test_tmall.py`（JSONL 逐行解析 + extracted_items 提取）
  - GREEN: 逐行 `json.loads()`，提取 `extracted_items[]`，合并去重
  - ⚠️ 不是标准 JSON（`json.load()` 会报 Extra data），必须逐行解析
  - 输出：`ProductRecord(item_id, price, title, shop)`，price 需从 str cast 为 float

- [ ] **T013** `ingestion/rose.py` — ROSE **JSONL** → `ProductRecord[]`（58 dump / 2853 商品 / 10+品牌）
  - RED: `tests/test_ingestion/test_rose.py`（JSONL + brand 从 title 提取）
  - GREEN: 同 TMALL JSONL 解析；额外：从 title 匹配 known brands（CROCS/HUGO BOSS/Adidas/Anta/UGG 等）
  - 输出：`ProductRecord(item_id, original_price, show_price, ump_price, title, shop, brand)`

- [ ] **T014** `tools/json_loader.py` — `JSONLoaderTool`（通用 JSON 加载，按 source 参数分发到对应 ingestion）
  - RED: `test_json_loader_jd` / `test_json_loader_tmall` / `test_json_loader_rose`
  - GREEN: 构造时注入 `data_root`；`execute({source: "JD"})` 分发到 `ingestion.jd.parse()`

- [ ] **T015** `tools/analysis.py` — `AnalysisTool`（对比/聚合/趋势，claim 可追溯到 raw data 行）
  - RED: `test_analysis_tool_compare_jd_vs_tmall`
  - GREEN: 接收已加载 records，执行计算，返回 `ToolResult`

**M1 验收**：4 个 ingestion 测试套件全绿；`CSVLoaderTool` + `JSONLoaderTool` + `AnalysisTool` 可被 Agent 正确调用。

---

## M2 — CLI Adapter（Transport，ADR-004）

**目标**：CLI 可用，`petfish-bi "查询"` 输出 JSON。

- [ ] **T020** `main.py` — typer CLI entrypoint（`ask` 命令）
  - RED: `tests/test_cli.py::test_cli_ask_returns_json`（用 `typer.testing.CliRunner`）
  - GREEN: `app = typer.Typer()`；`@app.command()` 调 `BIApplication.execute()`，输出 JSON 到 stdout
  - 参数：`--data-source`（多选）、`--output`（文件路径）、`--budget-tokens`、`--session-id`（resume）

- [ ] **T021** `main.py` — `--output outputs/report.json` 写文件
  - RED: `test_cli_output_to_file`
  - GREEN: typer Option；写文件前确认目录存在

- [ ] **T022** `main.py` — `--session-id` resume 之前分析
  - RED: `test_cli_resume_session`
  - GREEN: 从 `BIApplication.get_session()` 恢复

- [ ] **T023** `config/settings.py` — 路径配置（references/、outputs/）、模型选择
  - RED: `test_settings_default_paths`
  - GREEN: 从环境变量读取 API key、默认路径

- [ ] **T024** Rich text 输出（可选，ADR-003 nice-to-have）
  - RED: `test_cli_rich_output_format`
  - GREEN: `--format rich` 时输出 Markdown/HTML，与 JSON 解耦

**M2 验收**：`uv run petfish-bi "CROCS 在京东和天猫的价格差异"` 输出合法 JSON；`typer CliRunner` 集成测试通过。

---

## M3 — Web Adapter（async + Job Polling，ADR-007）

**目标**：FastAPI server 提供同样的 BIApplication 能力。

- [ ] **T030** `web/server.py` — FastAPI app + `BIApplication` 注入
  - RED: `tests/test_web/test_analyze.py::test_post_analyze_returns_202_job_id`
  - GREEN: `app = FastAPI()`；`POST /analyze` 接收 `BIQuery`，调 `execute_async()`，返回 `{"job_id": "...", "status": "pending"}` + Location header

- [ ] **T031** `jobs.py` — `JobRegistry`（in-memory dict，ADR-007）
  - RED: `test_job_registry_create_and_get`
  - GREEN: `dict[job_id, JobStatus]`；`create()`/`get()`/`update()`；并发用 `threading.Lock`

- [ ] **T032** `web/routes.py` — `GET /jobs/{id}` polling endpoint
  - RED: `test_get_job_returns_running_then_completed`
  - GREEN: 从 JobRegistry 查状态；completed 时返回 BIReport

- [ ] **T033** `application.py` — `execute_async(BIQuery) → job_id`
  - RED: `test_execute_async_returns_job_id_and_eventually_completes`
  - GREEN: `asyncio.create_task(self._run_agent_async(...))`；结果写回 JobRegistry

- [ ] **T034** Web 错误处理：`BudgetExceeded` → HTTP 200 + `status: budget_exceeded`（非 500）
  - RED: `test_web_budget_exceeded_returns_structured_error`
  - GREEN: 在 transport 层将 `BIReport(status="budget_exceeded")` 透传

- [ ] **T035** OpenAPI schema 自动生成（FastAPI 原生）
  - RED: `test_openapi_schema_has_analyze_and_jobs`
  - GREEN: FastAPI 自动；补充 `response_model` 声明

**M3 验收**：`uvicorn web.server:app` 启动；`POST /analyze` 返回 job_id；`GET /jobs/{id}` 最终返回 BIReport。

---

## M4 — Real Model + 部署准备（后续）

- [ ] **T040** Real-model smoke suite（`tests/smoke/`，env-gated `BI_CLI_RUN_REAL_MODEL=1`）
- [ ] **T041** OpenAI / Anthropic model adapter 接入（`framework.py` 内）
- [ ] **T042** Dockerfile + docker-compose（CLI + Web）
- [ ] **T043** CI pipeline（pytest + ruff + mypy，smoke 跳过）
- [ ] **T044** Session 持久化（EventStore → 文件/DB，支持重启后 resume）

---

## Doing

_（暂无 — 等待用户确认架构后开始 T001）_

## Done

- [x] **T000** 项目初始化（profile=code, AGENTS.md/README/pyproject/tasks 就绪, uv sync + git init 完成）
- [x] **ARCH** 架构文档完成（`docs/architecture.md`，ADR-004~010，基于 Oracle 分析 + 框架源码验证 + Momus 审查）
- [x] **DOMAIN** BI Domain Intelligence 规划完成（`docs/bi-domain-intelligence.md`，ADR-011~015，基于 4 路 agent 研究 + 4 源真实数据分析）
