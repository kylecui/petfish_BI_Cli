# petfish_BI_Cli

## Overview

**AI for BI** CLI 应用：客户通过 CLI 发出咨询请求，系统从电商原始数据（CSV/JSON，格式未必统一）中获取信息，按需协助分析，最终返回 **JSON 报告（必须）+ 富文本内容（加分）**。

基于 [petfishframework](https://pypi.org/project/petfishframework/) 构建 AI Agent 编排层 —— 利用其 event-sourced Session（可审计、可重放）、MCP-first Tool contracts、Pass^k 可靠性度量。

## Architecture

```text
Client (CLI query)
   │
   ▼
┌─────────────────────────────────────┐
│  Agent (petfishframework)           │
│  model + ReAct reasoning + tools    │
│  ├─ CSVIngestionTool                │  ← references/*.csv
│  ├─ JSONIngestionTool               │  ← references/*.json
│  ├─ AnalysisTool                    │
│  └─ ReportTool                      │  → outputs/*.json
└─────────────────────────────────────┘
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

本项目已验证 SiliconFlow Qwen2.5-72B-Instruct 模型。以下是实际可用的配置方式。

### 方式一：SiliconFlow Qwen2.5-72B（已验证）

```bash
# 1. 安装
uv sync --extra dev --extra openai

# 2. 配置 .env（从 .env.example 复制后填写）
cp .env.example .env
# 编辑 .env：
#   OPENAI_API_KEY=sk-your-siliconflow-key
#   OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 3. 配置 configs/bi_cli.yml
# 编辑 model.name 为 Qwen/Qwen2.5-72B-Instruct

# 4. 运行
uv run petfish-bi ask "CROCS在京东的均价是多少？"

# 5. 测试（FakeModel，无需 API key）
uv run pytest
```

### 方式二：OpenAI GPT-4o（未验证但应兼容）

```bash
uv sync --extra dev --extra openai
export OPENAI_API_KEY="sk-..."
uv run petfish-bi ask "CROCS在京东的均价是多少？"
```

### 样例输出

查看 `outputs/sample-*.json` 了解真实查询的 JSON 报告格式。

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
