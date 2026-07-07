# Backlog — TDD Task Breakdown

> 架构依据：`docs/architecture.md`（ADR-004~010）
> 方法论：Outside-in TDD（ADR-009）— 每个 TASK 从失败测试开始（Red → Green → Refactor）
> 执行顺序严格自上而下；跨 milestone 的 TASK 可并行（如 M1 的 4 个 ingestion adapter）

---

## M0 — Core Wiring（BIApplication 端到端 FakeModel）

**目标**：跑通 `BIApplication.execute(BIQuery) → BIReport` 的最小路径，验证架构 wiring 正确。

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

- [ ] **T004** `application.py` — `BIApplication.execute(BIQuery) → BIReport`（同步路径）
  - RED: `tests/test_bi_application.py::test_execute_returns_correct_report`（**架构验证测试 — ADR-009 第一个测试**）
  - 用 `FakeModel.script_tool_then_answer(tool_name="load_csv", tool_args={...}, final_answer=<合法JSON>)` 配置 Agent
  - ⚠️ **FakeModel API**：参数名是 `tool_name`（非 `tool_call`）、`final_answer`（非 `answer_template`）。`final_answer` 是字面字符串，不是模板；必须是合法 JSON 匹配 BIReport dataclass 字段。详见 `docs/architecture.md` §5.1。
  - 断言 `report.status == "ok"` 且 `report.data["total_sales"]` 含从 fixture 计算的真实值
  - GREEN: 实现 `BIApplication.__init__(agent, data_root)` + `execute(query)`
  - **内部流程**：`agent.run_structured(Task(prompt=query.prompt), BIReport)` 返回 `StructuredResult[BIReport]`；`execute()` 解包 `result.data`（BIReport）。若 `result.parse_error` 不为 None，返回 `BIReport(status="parse_error", answer=result.answer)`。捕获 `BudgetExceeded` → `BIReport(status="budget_exceeded")`。

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

- [ ] **T010** `ingestion/crocs.py` — CROCS CSV → `SalesRecord[]`
  - RED: `tests/test_ingestion/test_crocs.py`（正常记录 + 缺字段 + 编码异常）
  - GREEN: 解析 `references/CROCS_原始数据_*.csv`

- [ ] **T011** `ingestion/jd.py` — JD JSON dump → records
  - RED: `tests/test_ingestion/test_jd.py`
  - GREEN: 解析 `references/JD_CROCS_Raw_Memory_Dump.json`（注意 dump 结构差异）

- [ ] **T012** `ingestion/tmall.py` — TMALL JSON dump → records
  - RED: `tests/test_ingestion/test_tmall.py`
  - GREEN: 解析 `references/TMALL_CROCS_Raw_Memory_Dump.json`

- [ ] **T013** `ingestion/rose.py` — ROSE JSON + HTML 报告 → records
  - RED: `tests/test_ingestion/test_rose.py`
  - GREEN: JSON 先行（`ROSE_10BRANDS_Raw_Dump.json`）；HTML parser 延后（M2）

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
- [x] **ARCH** 架构文档完成（`docs/architecture.md`，ADR-004~010，基于 Oracle 分析 + 框架源码验证）
