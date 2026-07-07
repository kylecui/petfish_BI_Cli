# Architecture — petfish_BI_Cli

> AI for BI CLI，基于 [petfishframework](https://pypi.org/project/petfishframework/) v0.1.4。
> 核心约束：规划优先 / 测试驱动 / CLI↔Web 同构。

## 1. 设计原则

| 原则 | 落地方式 |
|---|---|
| **规划优先** | 架构文档 + ADR 先于代码；所有重大决策可追溯 |
| **测试驱动** | Outside-in TDD：从 BIApplication 端到端测试（FakeModel）开始，向下钻取 |
| **CLI↔Web 同构** | Transport adapter 模式：CLI (typer) 与 Web (FastAPI) 是同一 BIApplication 的两个 adapter |

## 2. 分层架构

```text
┌─────────────────────────────────────────────────────┐
│  Transport Layer (thin, no business logic)          │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │ CLI Adapter  │    │ Web Adapter (FastAPI)     │   │
│  │ (typer)      │    │ POST /analyze → 202+job_id│   │
│  │              │    │ GET /jobs/{id} → poll     │   │
│  └──────┬───────┘    └────────────┬─────────────┘   │
│         │       BIApplication     │                  │
│         ▼                         ▼                  │
├─────────────────────────────────────────────────────┤
│  Application Layer (core, no transport deps)        │
│  ┌─────────────────────────────────────────────────┐│
│  │ BIApplication                                    ││
│  │ ├── execute(BIQuery) → BIReport       (sync)    ││
│  │ ├── execute_async(BIQuery) → JobId    (async)   ││
│  │ └── get_job(job_id) → JobStatus                 ││
│  │                                                  ││
│  │ JobRegistry (in-memory dict, M0)                ││
│  └─────────────────────┬──────────────────────────┘│
│                        │ Agent + Session            │
│                        ▼                            │
├─────────────────────────────────────────────────────┤
│  Framework Layer (petfishframework, immutable)      │
│  ┌─────────────────────────────────────────────────┐│
│  │ Agent (frozen dataclass, shared singleton)       ││
│  │  model + ReAct + tools + retriever              ││
│  │                                                  ││
│  │ Session (per-request, UUID, event-sourced)       ││
│  │  run() / run_async() / run_structured()          ││
│  └─────────────────────┬──────────────────────────┘│
│                        │                            │
│                        ▼                            │
├─────────────────────────────────────────────────────┤
│  Tool Layer (DI, stateless)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │CSVLoaderTool │ │JSONLoaderTool│ │AnalysisTool │ │
│  │ data_root:Path│ │ data_root:Path│ │             │ │
│  └──────────────┘ └──────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
                    references/*.csv|json  (M0 local files)
```

**禁止依赖方向**：Transport → Application → Framework/Tool。反向 import 禁止。Application 层不得 import `typer`/`fastapi`/`httpx`。

## 3. 核心组件

### 3.1 BIApplication（Application Layer 入口）

```python
# 概念接口（非最终实现）
class BIApplication:
    def __init__(self, agent: Agent, data_root: Path): ...

    def execute(self, query: BIQuery, budget: Budget | None = None) -> BIReport:
        """同步执行：快速查询（<30s）。CLI 默认路径。

        内部调用 agent.run_structured(Task(prompt=query.prompt), BIReport)，
        获得 StructuredResult[BIReport] 后解包：
          - result.data is not None → 返回 result.data（BIReport）
          - result.parse_error is not None → 返回 BIReport(status="parse_error", answer=result.answer)
        BudgetExceeded 异常 → 返回 BIReport(status="budget_exceeded")。
        """

    async def execute_async(self, query: BIQuery, budget: Budget | None = None) -> str:
        """异步执行：返回 job_id。长任务（>30s）。Web 默认路径。"""

    def get_job(self, job_id: str) -> JobStatus:
        """查询 job 状态：pending/running/completed/failed。"""

    def get_session(self, session_id: str) -> Session:
        """按 session_id 获取 Session（支持 resume）。"""
```

**错误处理**（三层）：
1. `BudgetExceeded` → 捕获，返回 `BIReport(status="budget_exceeded")`
2. `StructuredResult.parse_error` 不为 None → 返回 `BIReport(status="parse_error", answer=result.answer)`，保留原始模型输出用于调试
3. `BIReport.status` 在 transport 层映射：CLI 打印 warning；Web 返回 HTTP 200 + status 字段（**非 500**）

### 3.2 Domain Models（dataclass，非 pydantic）

**关键决策**：框架的 `agent.run_structured(task, BIReport)` 要求 `output_type` 是 `@dataclass`。因此核心域模型用 `@dataclass(frozen=True)`；pydantic 仅用于 API 边界（CLI 参数校验 / Web request/response schema）。

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class BIQuery:
    prompt: str
    data_sources: tuple[str, ...] = ()     # ["CROCS", "JD", "TMALL", "ROSE"]
    metadata: dict = field(default_factory=dict)          # ⚠️ 非 dict[str, Any]

@dataclass(frozen=True)
class BIReport:
    answer: str                            # 分析结论
    data: dict                             # ⚠️ 非 dict[str, Any] — 见下方说明
    session_id: str = ""
    usage: dict = field(default_factory=dict)
    rich_content: str | None = None        # Markdown/HTML（nice-to-have）
    status: str = "ok"                     # ok | budget_exceeded | error | parse_error
```

> **⚠️ 框架限制（v0.1.4）**：`petfishframework.core.structured._coerce_value()` 在 line 176 调用 `isinstance(value, field_type)`。对参数化泛型（`dict[str, Any]`/`tuple[str, ...]`）会抛 `TypeError: isinstance() argument 2 cannot be a parameterized generic`，导致 `run_structured()` 返回 `StructuredResult(data=None, parse_error="...")`。
> **因此核心域模型一律用非参数化类型**（`dict` 而非 `dict[str, Any]`、`tuple` 而非 `tuple[str, ...]`）。当框架修复此限制后可恢复参数化标注。详细验证见 Momus 审查 Issue #2。

### 3.3 Agent（Framework Layer，共享单例）

```python
# Agent 是 frozen dataclass，进程级共享安全
bi_agent = Agent(
    model=model,                    # OpenAI/Anthropic/FakeModel
    reasoning=ReAct(),
    tools=(
        CSVLoaderTool(data_root=references_path),
        JSONLoaderTool(data_root=references_path),
        AnalysisTool(),
    ),
)
```

**为什么共享安全**：`Agent` 是 `@dataclass(frozen=True)`。每次 `agent.session(task)` 新建独立 `Session`（独立 UUID + EventEmitter + Budget）。并发请求各自隔离。

### 3.4 Tool Layer（DI，无状态）

Tool 实现 petfishframework `Tool` Protocol（`name`/`description`/`input_schema`/`risk_level`/`capabilities`/`execute()`）。依赖在构造时注入：

```python
class CSVLoaderTool:                  # implements Tool Protocol
    name = "load_csv"
    risk_level = RiskLevel.LOW
    capabilities = ("fs:read",)

    def __init__(self, data_root: Path):
        self._data_root = data_root   # 构造时注入，不持有可变状态

    def execute(self, args: dict) -> ToolResult:
        path = self._data_root / args["filename"]
        # 读 CSV → 返回结构化记录
```

**禁止**：Tool 内 `self._cache`（除非线程安全）；Tool 内 `print()`/`sys.exit()`（transport 泄漏）。

## 4. 并发模型

### 4.1 CLI（同步）

```text
User → typer command → BIApplication.execute(BIQuery) → BIReport → stdout / outputs/*.json
```

单用户，阻塞等待。即使分析耗时 5 分钟，用户等待可接受。

### 4.2 Web（异步 + Job Polling）

```text
Client → POST /analyze → BIApplication.execute_async(BIQuery) → 202 {job_id}
                                          │
                            asyncio.create_task(agent.run_async())
                                          │
Client ← GET /jobs/{job_id} ← JobRegistry ←──── Result
```

**JobRegistry（M0 in-memory）**：

```python
@dataclass
class JobStatus:
    job_id: str
    status: str          # pending | running | completed | failed
    result: BIReport | None = None
    error: str | None = None
    created_at: float = 0.0
    completed_at: float | None = None

# M0: dict[job_id, JobStatus]
# 后续: Redis / DB（当需要多 worker 或持久化时）
```

**不用 Celery / Redis**，直到出现多 worker 需求。单 FastAPI 进程 + asyncio + in-memory dict 足够。

### 4.3 已验证的并发安全前提

| 前提 | 源码验证 |
|---|---|
| Session ID = UUID（无碰撞） | ✅ `session.py:40` — `uuid.uuid4().hex[:16]` |
| EventEmitter 每 Session 独立 | ✅ `agent.py:165` — `events = EventEmitter()` 每 `session()` 新建 |
| Budget 每 Session 独立 | ✅ `session.py:38` — 实例字段 |
| Agent frozen=True（只读共享） | ✅ `agent.py:20` — `@dataclass(frozen=True)` |
| 框架原生 `run_async()` | ✅ `agent.py:54` / `session.py:51` |
| ConversationStore 可选 | ✅ `session.py:43` — `None` 时不持久化；多用户 Web 各自独立 `conversation_id` |

## 5. 测试策略（Outside-in TDD）

### 5.1 第一个失败测试

```python
# tests/test_bi_application.py
def test_bi_application_returns_correct_total_sales():
    """Given CROCS CSV fixture and a sales query,
    BIApplication.execute returns BIReport with correct total."""
    # FakeModel.script_tool_then_answer(tool_name, tool_args, final_answer)
    # final_answer 必须是合法 JSON（匹配 BIReport dataclass 字段），
    # 因为 agent.run_structured 会解析它。
    # ⚠️ 不是模板语法；final_answer 是 ModelResponse.content 的字面值。
    fake_model = FakeModel.script_tool_then_answer(
        tool_name="load_csv",                           # 非 tool_call
        tool_args={"filename": "CROCS_sample.csv"},
        final_answer=(                                  # 非 answer_template
            '{"answer": "CROCS 2024 Q3 总销售额为 12345.67", '
            '"data": {"total_sales": 12345.67}, '
            '"status": "ok"}'
        ),
    )
    app = BIApplication(
        agent=Agent(
            model=fake_model,
            reasoning=ReAct(),
            tools=(CSVLoaderTool(data_root=FIXTURES_DIR),),
        ),
        data_root=FIXTURES_DIR,
    )
    query = BIQuery(prompt="CROCS 2024 Q3 总销售额", data_sources=("CROCS",))
    report = app.execute(query)

    assert report.status == "ok"
    assert report.data["total_sales"] == 12345.67  # 从 fixture 计算的真实值
```

此测试迫使你定义 `BIQuery`/`BIReport`/`BIApplication`/`CSVLoaderTool`，同时用 FakeModel 保证确定性。**数据与计算是真实的**。

### 5.2 测试金字塔

```
                    ┌──────────────┐
                    │  E2E (real   │  ← 环境变量门控，发布前手动跑
                    │  model)      │
                   /└──────────────┘
              ┌────────────────┐
              │ CLI/Web 集成   │  ← typer CliRunner / FastAPI TestClient
              └────────────────┘
            ┌────────────────────┐
            │ BIApplication      │  ← FakeModel + 真 Tools + 真 fixture
            │ (端到端 FakeModel) │
            └────────────────────┘
          ┌─────────────────────────┐
          │ Agent integration       │  ← FakeModel，验证 tool 调用序列
          └─────────────────────────┘
        ┌─────────────────────────────┐
        │ Tool 单元测试               │  ← 给路径，返回正确记录
        └─────────────────────────────┘
      ┌──────────────────────────────────┐
      │ Ingestion 适配器（每数据源一套） │  ← CROCS CSV / JD JSON / TMALL JSON / ROSE HTML
      └──────────────────────────────────┘
    ┌───────────────────────────────────────┐
    │ Domain unit（BIQuery/BIReport/dataclass）│
    └───────────────────────────────────────┘
```

### 5.3 TDD 规则

1. **每个功能从失败测试开始**（Red → Green → Refactor）。
2. **FakeModel 用于所有自动化测试**——不依赖真实 API key，确定性。
3. **Real-model smoke suite** 在 `tests/smoke/` 下，环境变量 `BI_CLI_RUN_REAL_MODEL=1` 时运行，CI 默认跳过。
4. **每数据源一套 ingestion 测试**——不写"通用 parser"测试。

## 6. 架构决策记录（ADR）

### ADR-004: Service-layer（BIApplication）与 Transport 解耦

**决策**：BIApplication 是唯一的 Application Layer 入口，Transport（CLI/Web）只做 I/O 转发。

**理由**：CLI↔Web 同构要求核心逻辑不依赖 transport。`BIApplication` 无 `typer`/`fastapi` import。

**后果**：Transport 层薄、可替换；BIApplication 可独立测试。

### ADR-005: Tool 是数据后端边界；M0 不建正式 DataPort

**决策**：Tool 直接持有 `data_root: Path`。不引入 `DataPort`/`Repository` Protocol 层。

**理由**：petfishframework 的 Tool 已是 MCP-shaped contract（本身即 port-adapter）。再叠一层 DataPort 是过早抽象。等出现第二个后端实现（S3/DB）时，再提取 Protocol——届时你知道真实需求，不是猜测。

**后果**：v1 代码更少；当 Web 真正需要 S3 时，可能需要小重构（成本 ~1 个 Tool 类）。

**反决策**：不预先建 `DataPort` Interface + `LocalFileAdapter` + `S3Adapter`。这是经典过度设计陷阱。

### ADR-006: Agent 进程级共享；Session 每请求独立

**决策**：Agent 作为模块级单例共享。每次请求 `agent.session(task)` 新建 Session。

**理由**：源码验证 Agent 是 `@dataclass(frozen=True)`；Session ID 是 UUID；EventEmitter 每 Session 新建。并发安全已确认。

**后果**：无需 Agent 池；内存效率高（Agent 构造成本 ~0，Session 才有状态）。

### ADR-007: CLI 同步；Web 异步 + Job Polling（in-memory JobRegistry）

**决策**：CLI 用 `BIApplication.execute()`（同步）；Web 用 `execute_async()` → job_id + `GET /jobs/{id}` polling。M0 JobRegistry 是 in-memory dict。

**理由**：框架已内置 `run_async()`，async 成本低。但 >60s 的请求会被 proxy 断开，需 job pattern。不引入 Celery/Redis 直到多 worker 需求出现。

**后果**：单进程 FastAPI 可支撑的并发受 Python GIL + LLM API rate limit 约束（通常足够）；多 worker 时升级 JobRegistry 即可，接口不变。

### ADR-008: Pin petfishframework>=0.1.4；框架适配层隔离

**决策**：`pyproject.toml` 固定 `petfishframework>=0.1.4,<0.2.0`。所有框架直接调用收敛到 `petfish_bi_cli/framework.py`（Agent 构建器、Session 工厂、Tool 基类 mixin）。

**理由**：框架处于 Alpha，API 可能变。集中适配点让升级可控。

**后果**：v0.2 发布时改一个模块而非全局搜索。

### ADR-009: Outside-in TDD，从 BIApplication + FakeModel 开始

**决策**：第一个失败测试是 `BIApplication.execute(BIQuery) → BIReport`（FakeModel + 真实 CSV fixture）。然后向下钻取写 Tool/Ingestion/Domain 单元测试。

**理由**：Inside-out（先 domain model）风险：建了 5 层才发现架构错。Outside-in 先验证 wiring，再补细节。

**后果**：早期测试较粗；但架构验证快。FakeModel 保证确定性，真实 fixture 保证数据/计算正确。

### ADR-010: 每数据源独立 ingestion adapter；禁止通用 parser

**决策**：CROCS CSV / JD JSON / TMALL JSON / ROSE HTML 各有独立 Loader。不写"自动检测格式"的通用 parser。

**理由**：格式异构（CSV vs JSON dump vs HTML 报告），字段名/结构/编码各异。通用 parser 会变成 bug 温床。

**后果**：N 个数据源 = N 个 Loader 类。代码重复可接受（每源逻辑不同）；可测试性好（每源独立测试套件）。

## 7. 目录结构（实现时填充）

```text
src/petfish_bi_cli/
├── __init__.py
├── main.py                    # typer CLI entrypoint（Transport adapter）
├── application.py             # BIApplication（Application Layer）
├── domain.py                  # BIQuery, BIReport, JobStatus (dataclass)
├── framework.py               # Agent 构建器 + Session 工厂（适配层，ADR-008）
├── jobs.py                    # JobRegistry（in-memory，ADR-007）
├── tools/
│   ├── __init__.py
│   ├── csv_loader.py          # CSVLoaderTool（CROCS）
│   ├── json_loader.py         # JSONLoaderTool（JD / TMALL / ROSE）
│   └── analysis.py            # AnalysisTool
├── ingestion/
│   ├── __init__.py
│   ├── crocs.py               # CROCS CSV → records
│   ├── jd.py                  # JD JSON → records
│   ├── tmall.py               # TMALL JSON → records
│   └── rose.py                # ROSE HTML/JSON → records
└── config/
    └── settings.py            # 路径、模型配置

tests/
├── test_bi_application.py     # 第一个失败测试（ADR-009）
├── test_domain.py
├── test_tools/
├── test_ingestion/
├── test_cli.py                # typer CliRunner
└── smoke/                     # real model（env-gated）

# Web adapter（M2 阶段加入，不在 src/petfish_bi_cli 内，独立模块）
web/
├── server.py                  # FastAPI app
└── routes.py                  # POST /analyze, GET /jobs/{id}
```

## 8. 质量门禁

- [ ] `BIApplication` 模块无 `import typer`/`import fastapi`（transport 隔离）
- [ ] 所有 Tool `execute()` 无 `print()`/`sys.exit()`/文件写入（纯函数行为）
- [ ] `BudgetExceeded` 被 BIApplication 捕获，返回结构化 JSON，不抛 500
- [ ] FakeModel 测试覆盖率 ≥ 80%（core + tools + application）
- [ ] 每数据源有独立 ingestion 测试套件
- [ ] Real-model smoke suite 存在（env-gated）
