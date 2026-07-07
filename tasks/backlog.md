# Backlog

## To Do

### M0 — CLI 骨架 + 最小可运行

- [ ] **T001** 搭建 `src/petfish_bi_cli/` 包骨架：`main.py` (typer entry)、`__init__.py`、`config/settings.py`
- [ ] **T002** 定义 pydantic 数据模型：`BIQuery`（用户咨询）、`BIReport`（JSON 输出 schema）
- [ ] **T003** 实现 `CSVIngestionTool`（继承 petfishframework `Tool`）：读取 `references/CROCS_*.csv`，返回结构化记录
- [ ] **T004** 实现 `JSONIngestionTool`：分别适配 JD / TMALL / ROSE 三种 JSON dump 结构
- [ ] **T005** 定义最小 BI Agent：`Agent(model=..., reasoning=ReAct(), tools=(CSVIngestionTool, JSONIngestionTool))`
- [ ] **T006** 实现 CLI 命令 `petfish-bi "<query>"` → 调用 Agent → 输出 JSON 到 stdout 与 `outputs/`

### M1 — 分析能力 + 可靠性

- [ ] **T007** 实现 `AnalysisTool`：基于检索到的数据做对比/聚合/趋势分析（claim 必须可追溯到 raw data 行）
- [ ] **T008** 实现 `ReportTool`：把 Agent 输出转成 pydantic 校验过的 JSON 报告
- [ ] **T009** 写 FakeModel 测试：验证 Agent trajectory、Tool 调用、JSON schema 校验（无需 API key）
- [ ] **T010** 添加 Budget 配置：限制单次咨询的 token/step 上限

### M2 — 富文本输出 + 多数据源

- [ ] **T011** 富文本报告生成器（Markdown/HTML，可选输出，与 JSON 解耦）
- [ ] **T012** ROSE HTML 报告 ingestion adapter（解析现有 `ROSE_10BRANDS_Price_Intelligence_Report.html`）
- [ ] **T013** 跨数据源关联分析（JD vs TMALL 价格对比、ROSE 10 品牌横评）

## Doing

_（暂无）_

## Done

- [x] **T000** 项目初始化（profile=code, src 布局, pydantic+ruff+pytest 配置, AGENTS.md/README/tasks 就绪）
