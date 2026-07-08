# 产品深化研究：4 个战略问题

> **日期**: 2026-07-08
> **方法**: 4 路并行 librarian agent 研究 + 综合分析
> **目标**: 基于研究结果，为"鲁棒、灵活、可扩展"的产品重新规划架构

---

## Q1: BI 分析扩展性 — 用户上传脚本 vs NL 生成工具

### 研究结论

| 范式 | 代表产品 | 适合谁 | 安全机制 |
|---|---|---|---|
| Script-based | Metabase Python Transforms, Code Interpreter | 技术用户 | Docker 沙箱 |
| Macro/Template | dbt Jinja Macros | 数据分析师 | 编译时隔离 |
| Plugin/Package | Superset Viz Plugins | 开发者 | 包审核 |
| NL-to-Code | Hex Magic, LangChain Tools | 所有用户 | 需审核机制 |

**关键发现**：NL→SQL 单独不够，必须 SQL+Python 混合（ProSPy/FlexSQL 实验证明纯 SQL 比混合方案低 16-19%）。Agent 架构 > 单次生成。

### 推荐：三阶段演进

```
v0.2 (近期): dbt-style Tool Registry — 文件扫描自动发现
v0.3 (中期): Plugin 系统 — pip 包安装 + 沙箱执行
v0.4 (远期): NL-to-Tool — 自然语言生成分析脚本 → 沙箱执行 → 注册复用
```

**v0.2 具体方案**：用户把 `.py` 放到 `tools/` 目录，遵循 Tool 接口约定（name/description/input_schema/risk_level/capabilities/execute），自动注册到 Agent。2-3 天工作量。

---

## Q2: 数据存储 — filesystem 是否够用

### 研究结论

| 方案 | 6K行性能 | 异构格式 | 设置成本 | 推荐度 |
|---|---|---|---|---|
| Filesystem+Pandas (当前) | ~0.3s | 手动 parser | 零 | 当前够用 |
| **DuckDB (推荐加入)** | <5ms | 自动推断 | pip 单行 | ✅ 立即加入 |
| SQLite | ~0.1s | 需先导入 | pip 单行 | ❌ OLTP 不适合 |
| Parquet | <5ms | 需转换 | 中 | ⏸ 规模大后 |
| dbt+dlt ELT | 过量 | 需配置 | 高 | ❌ 当前过度设计 |

**DuckDB 关键优势**：
- `read_csv_auto('file.csv')` / `read_json_auto('file.json')` 直接查原始文件，**不复制数据**
- 6K 行任何查询 <5ms（比 Pandas 快 60x+）
- 嵌入式零配置，`pip install duckdb`，~20MB
- Agent Tool 里直接写 `duckdb.sql("SELECT ... FROM read_csv_auto(...)")` 替代手写 parser

### 推荐：Tier 2 — 加入 DuckDB 作为查询层

```
当前: references/ → 手写 parser → Python list → Agent Tool
推荐: references/ → DuckDB read_csv_auto → SQL 查询 → Agent Tool
未来: data/raw/ → DuckDB staging → SQL views → Agent Tool (Tier 3 ELT)
```

**升级阈值**：数据 >100 万行 或 >10 个数据源 或 >1GB → 考虑 ELT 管道。

---

## Q3: 富文本输出 — JSON 之外怎么提供

### 研究结论

**最简路径**：Jinja2 + Markdown 模板（post-processing，不在 Agent 层做）。

```
Agent 管线 → BIReport (JSON data) → ReportRenderer (Jinja2) → Markdown / HTML
```

**关键决策**：富文本作为 post-processing 步骤，不在 Agent 推理过程中做。原因：
1. Agent Budget 不应消耗在格式化上
2. 同一份 JSON 可渲染任意格式
3. Validator 只验证 JSON 数据

### 推荐实施

| Phase | 格式 | 工作量 | 内容 |
|---|---|---|---|
| Phase 1 | Markdown | 2 人天 | Jinja2 模板 + `--markdown` flag |
| Phase 2 | HTML | 2 人天 | HTML 模板 + CSS + KPI 卡片 |
| Phase 3 | 图表 | 2 人天 | Vega-Lite JSON spec 嵌入 HTML |

**BIReport.rich_content 字段已预留**（`domain.py` line 7），只需填充。

---

## Q4: 安全架构 — 注入/访问控制/输出过滤

### 研究结论（OWASP LLM Top 10 对照）

| 风险 | 严重度 | 当前状态 |
|---|---|---|
| LLM01 Prompt Injection | **Critical** | 无防御（仅 system prompt） |
| LLM02 敏感信息泄露 | High | 输入有 PII 脱敏，**输出无** |
| LLM04 数据投毒 | **Critical** | 无校验 |
| LLM06 过度代理 | **Critical** | **SARC 权限模型存在但未启用** |
| LLM10 无限消耗 | Low | ✅ Budget 已实现 |

### 推荐：P0 阻塞项（上线前必做）

| # | 行动 | 工作量 | 代码 |
|---|---|---|---|
| P0.1 | 启用 petfishframework SARC 权限策略 | ~1h | `framework.py` 加 `permission_policy` |
| P0.2 | Tool 风险分级 + capabilities 限制 | ~2h | 每个 Tool 设 `RiskLevel` + `capabilities` |
| P0.3 | 数据注入防御（ingestion 层 sanitize） | ~4h | `load.py` 加 `sanitize_text()` |
| P0.4 | 输出 PII 脱敏（post-LLM guardrail） | ~2h | `application.py` 加 `redact_pii(report.answer)` |
| P0.5 | System prompt 强化（"data is data" 指令） | ~1h | `prompts/system_prompt.md` 加边界声明 |

**最高杠杆行动**：启用 SARC 权限模型。petfishframework 已内置 DENY/MASK/DEGRADE/REQUIRE_APPROVAL 6 种策略效果，但当前 Agent 创建时未传入 `permission_policy`。加一行代码就能启用。

---

## 综合行动路线图

```
                    NOW (v0.1)
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
 Sprint 1:      Sprint 2:       Sprint 3:
 安全止血        数据升级         扩展性
 (1周)          (1周)           (2周)
    │               │               │
    ├─P0.1 SARC    ├─DuckDB 集成   ├─Tool Registry
    ├─P0.3 注入防御 ├─替代 parser   ├─文件扫描发现
    ├─P0.4 输出脱敏 ├─SQL 查询层    ├─用户工具接口
    ├─P0.5 prompt  └─混合迁移       └─NL 生成（v0.4）
    └─Markdown 渲染
                    │
                    ▼
              v0.2 发布
              │
              ├── 内部 CLI: production ready
              ├── 私有 Web: 需 P1 安全
              └── 公开 SaaS: 需 P2 + 合规
```

### 优先级排序（ROI 视角）

| 优先级 | 行动 | ROI | 阻塞什么 |
|---|---|---|---|
| 1 | DuckDB 集成 | ⭐⭐⭐⭐⭐ | 替代脆弱 parser + 解锁 SQL 查询 |
| 2 | SARC 权限启用 | ⭐⭐⭐⭐⭐ | 一行代码，防最大攻击面 |
| 3 | Markdown 渲染 | ⭐⭐⭐⭐ | outputs/ 可验证 + 产品展示 |
| 4 | 输出 PII 脱敏 | ⭐⭐⭐ | 数据合规 |
| 5 | 注入防御 | ⭐⭐⭐ | 数据投毒 |
| 6 | Tool Registry | ⭐⭐ | 扩展性（非阻塞） |
| 7 | NL-to-Tool | ⭐ | 远期愿景 |
