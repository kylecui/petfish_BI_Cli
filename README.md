# petfish_BI_Cli

## Overview

**AI for BI** CLI 应用：客户通过 CLI 发出咨询请求，系统从电商原始数据（CSV/JSON，格式未必统一）中获取信息，按需协助分析，最终返回 **JSON 报告（必须）+ 富文本内容（加分）**。

基于 [petfishframework](https://pypi.org/project/petfishframework/) 构建 AI Agent 编排层 —— 利用其 event-sourced Session（可审计、可重放）、MCP-first Tool contracts、Pass^k 可靠性度量。

## Architecture

```text
Client (CLI / Web API)
   │
   ▼
┌──────────────────────────────────────────────┐
│  BIApplication                                │
│  ├── Agent (petfishframework)                 │
│  │   model + ReAct + tools + permission       │
│  │   ├── ExploreDataSourcesTool (config-driven)│
│  │   ├── LoadDataTool (config-driven)          │
│  │   ├── SentimentAnalysisTool                 │
│  │   ├── TrendTool                             │
│  │   ├── CrossSourceComparisonTool             │
│  │   ├── CrossTimeTool                         │
│  │   └── ScriptTool × N (customer scripts)     │
│  │                                            │
│  ├── Grounding: ClaimsRegistry + Validator    │
│  ├── Permission: YamlPolicy + MASK            │
│  ├── Audit: SIEMSink + PII Redaction          │
│  └── Rendering: ReportRenderer (Jinja2)       │
│                                              │
│  Config: configs/bi_cli.yml                   │
│  ├── model / budget / data                    │
│  ├── sources (data source declarations)       │
│  ├── scripts (customer BI scripts)            │
│  ├── templates (output rendering)             │
│  ├── rag (document retrieval)                 │
│  └── vault (credential management)            │
└──────────────────────────────────────────────┘
   │
   ▼
JSON report (must-have) + rich content (nice-to-have)
```

## Data Sources (references/)

| 文件 | 类型 | 来源 |
|---|---|---|
| `CROCS_原始数据_20260605_144849.csv` | CSV | CROCS 商品数据 |
| `JD_CROCS_Raw_Memory_Dump.json` | JSON | 京东 CROCS 原始 dump |
| `TMALL_CROCS_Raw_Memory_Dump.json` | JSON | 天猫 CROCS 原始 dump |
| `ROSE_10BRANDS_Raw_Dump.json` | JSON | ROSE 10 品牌原始 dump |
| `ROSE_10BRANDS_Price_Intelligence_Report.html` | HTML | ROSE 价格情报报告样本 |

⚠️ 各数据源格式不统一，每个源需独立 ingestion adapter。

## Quick Start

```bash
# 1. 一键安装
./install.sh

# 2. 配置（或运行 petfish-bi config init 交互式生成）
cp configs/bi_cli.example.yml configs/bi_cli.yml
export OPENAI_API_KEY="sk-..."

# 3. 查询
petfish-bi ask "CROCS在京东的均价是多少？"

# 4. 健康检查
petfish-bi health

# 5. 启动 Web API
petfish-bi web
```

详细使用说明见 [docs/user-guide.md](docs/user-guide.md)。

部署指南见 [DEPLOY.md](DEPLOY.md)。

## Development

```bash
# Lint
uv run ruff check .

# 类型检查
uv run mypy src/

# 格式化
uv run ruff format .
```

## Project Layout

详见 `AGENTS.md` 的 Directory Map。核心：`src/petfish_bi_cli/`（CLI + Agent + Tools）、`tests/`、`references/`（原始数据）、`outputs/`（生成报告）。

## Future Research Directions

- BI 分析深化（价格情报、竞品对比、趋势）
- 舆情分析（品牌、代言人 sentiment）
- 反馈分析（评论、评分挖掘）
- petfishframework 框架本身的演进研究

研究能力已通过 `research-skill-pack`（54 个 skill）就绪。

## Quality Control

合并/发布前运行 `qa/code-review-checklist.md` 与 `qa/test-plan.md`。
