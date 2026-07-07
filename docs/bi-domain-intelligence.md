# BI Domain Intelligence Layer

> 补充 `docs/architecture.md` 的领域智能层规划。
> 基于 4 路 agent 研究（BI 查询框架 / 框架 prompt 注入点 / LLM grounding / 生产 prompt 模板）+ 4 源真实数据分析。

## 1. 为什么需要这一层

`docs/architecture.md` 的 Transport → BIApplication → Agent → Tools → Data 分层是**技术管道**，但不包含 BI 领域智能：

| 缺失 | 后果 |
|---|---|
| 查询理解 | "CROCS 在京东和天猫的价格差异" → Agent 不知道要先加载 JD + TMALL 数据 |
| 语义层 | Agent 不知道"CROCS"是品牌、"京东"是平台、数据里没有"销售额"字段 |
| Grounding | Agent 会用模型常识说"CROCS是流行鞋品牌"而非从评论数据挖真实反馈 |
| 输出校验 | BIReport.data 里的数字是真的计算结果还是模型编的？无法验证 |
| Prompt 工程 | 框架默认 ReAct prompt 是"You are a helpful assistant"，无 BI 约束 |

**核心洞察**（来自 TRACE / StatGuard / WrenAI 研究）：BI agent 的可信性不靠 prompt"请不要编"，靠**构造性约束**：

1. LLM 只看 metadata（统计摘要、行数、列名），不看 raw data
2. Tool 返回带 ID 的 claims，LLM 只能引用 claim ID
3. 输出校验做 substring 匹配——引用必须是 Tool 输出的逐字子串

## 2. 架构定位

```text
Transport (CLI/Web)
    ↓ 自然语言查询
┌──────────────────────────────────────────────────────┐
│ BI Domain Intelligence Layer                         │
│                                                      │
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │ Semantic Layer  │  │ BIAgentStrategy          │  │
│  │ (YAML metadata) │  │ (subclass ReAct)         │  │
│  │ references/     │  │ override _system_prompt()│  │
│  │ semantic/*.yml  │  │                          │  │
│  └────────┬────────┘  └──────────┬───────────────┘  │
│           │                      │                   │
│  ┌────────▼──────────────────────▼───────────────┐  │
│  │ Query Understanding Tools                      │  │
│  │  • explore_data_sources(query) → 元数据        │  │
│  │  • load_data(source, filters) → ClaimsLedger  │  │
│  │  • analyze(claims, operation) → 结果           │  │
│  │  • validate_output(report) → grounding check   │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
    ↓ JSON IR + grounded BIReport
BIApplication (Agent ReAct + Session)
    ↓
Tools (CSVLoader/JSONLoader/Analysis)
```

**关键设计**：Query Understanding 不是独立的 pre-processing 步骤，而是** Agent 调用的 Tools**。Agent 的 ReAct 循环自然执行：explore → load → analyze → validate → output。

## 3. Semantic Layer（YAML 元数据）

### 3.1 设计原则（Atlas / WrenAI 模式）

- 每数据源一个 YAML 文件，描述 schema、实体、指标、示例问题
- 版本化、可 diff、Git 友好
- Agent 通过 `explore_data_sources` Tool 读取（不直接读文件）

### 3.2 CROCS CSV 元数据（舆情/UGC 数据）

```yaml
# references/semantic/crocs_xiaohongshu.yml
source_id: crocs_xiaohongshu
source_type: csv
file_pattern: "CROCS_*.csv"
description: "小红书 CROCS 相关笔记与评论数据（用户生成内容）"

schema:
  columns:
    - name: 搜索关键词
      aliases: [search_keyword, keyword]
      type: string
      description: "小红站搜索关键词"
    - name: 笔记标题
      aliases: [note_title, title]
      type: string
    - name: 博主名
      aliases: [blogger, author]
      type: string
    - name: 笔记发布时间
      aliases: [note_date, publish_time]
      type: string
      format: "编辑于 MM-DD 或 YYYY-MM-DD"
    - name: 采集时间
      aliases: [crawl_time, collected_at]
      type: datetime
    - name: 评论人昵称
      aliases: [commenter, commenter_name]
      type: string
    - name: 评论内容
      aliases: [comment, comment_text]
      type: string
      description: "用户评论原文——舆情分析的核心字段"
    - name: 评论时间
      aliases: [comment_time]
      type: datetime
    - name: 是否近3天新增
      aliases: [is_new_3d, is_recent]
      type: boolean

entities:
  - name: brand
    values: ["CROCS", "卡骆驰"]
    source_column: 搜索关键词
  - name: sentiment_topic
    extractable_from: 评论内容
    examples: ["磨脚", "硬", "好看", "好穿", "贵", "便宜", "平替"]

metrics:
  - name: comment_count
    aliases: [评论数, 评论量]
    aggregation: count
    source_column: 评论内容
  - name: note_count
    aliases: [笔记数]
    aggregation: count_distinct
    source_column: 笔记标题
  - name: positive_ratio
    description: "正面评论占比（需 sentiment 分析）"
    compute: "positive_count / total_count"

example_questions:
  - "用户对CROCS云朵款的评价如何？"
  - "最常见的投诉是什么？"
  - "CROCS的平替讨论多吗？"
```

### 3.3 JD JSON 元数据（商品列表）

```yaml
# references/semantic/jd_products.yml
source_id: jd_products
source_type: json
file_pattern: "JD_CROCS_Raw_Memory_Dump.json"
description: "京东 CROCS 商品列表（价格、优惠券、库存）"

schema:
  json_path: "raw_data.search_results[]"
  columns:
    - name: skuId
      type: string
    - name: skuName
      aliases: [product_name, title]
      type: string
    - name: isJdSelf
      aliases: [is_self, jd_self]
      type: boolean
    - name: shopName
      aliases: [shop, store]
      type: string
    - name: originalPrice
      aliases: [原价, list_price]
      type: float
    - name: calculatedFinalPrice
      aliases: [final_price, 实付价]
      type: float
    - name: stockState
      type: int

entities:
  - name: brand
    values: ["CROCS", "卡骆驰"]
    source_column: skuName
  - name: platform
    values: ["JD", "京东"]
  - name: shop_type
    extractable_from: isJdSelf
    mapping: {true: "京东自营", false: "第三方"}

metrics:
  - name: avg_price
    aliases: [均价, 平均价格]
    aggregation: avg
    source_column: calculatedFinalPrice
  - name: min_price
    aliases: [最低价]
    aggregation: min
    source_column: calculatedFinalPrice
  - name: discount_amount
    compute: "originalPrice - calculatedFinalPrice"

example_questions:
  - "CROCS在京东的价格范围？"
  - "京东自营和第三方哪个便宜？"
```

### 3.4 TMALL / ROSE 元数据（JSONL API dump）

```yaml
# references/semantic/tmall_products.yml
source_id: tmall_products
source_type: jsonl
file_pattern: "TMALL_CROCS_Raw_Memory_Dump.json"
description: "天猫 CROCS 商品列表（API 抓取 dump）"

schema:
  jsonl_structure:
    each_line: "timestamp + source_url + extracted_items[] + raw_response"
    items_path: "extracted_items[]"
  item_columns:
    - name: itemId
      type: string
    - name: price
      type: float
      note: "字符串存储，需 cast"
    - name: title
      type: string
    - name: shop
      type: string

entities:
  - name: brand
    values: ["CROCS", "卡骆驰", "Crocs"]
    source_column: title
  - name: platform
    values: ["TMALL", "天猫"]
  - name: shop
    source_column: shop

metrics:
  - name: avg_price
    aggregation: avg
    source_column: price
  - name: shop_count
    aggregation: count_distinct
    source_column: shop

example_questions:
  - "天猫上CROCS有几家店在卖？"
  - "天猫CROCS的平均价格？"
```

```yaml
# references/semantic/rose_10brands.yml
source_id: rose_10brands
source_type: jsonl
file_pattern: "ROSE_10BRANDS_Raw_Dump.json"
description: "ROSE 10+品牌价格情报（跨品牌横评）"

schema:
  jsonl_structure:
    each_line: "timestamp + source_url + extracted_items[] + raw_response"
    items_path: "extracted_items[]"
  item_columns:
    - name: itemId
    - name: original_price
      type: float
    - name: show_price
      type: float
    - name: ump_price
      type: float
      description: "实际到手价"
    - name: title
    - name: shop

entities:
  - name: brand
    extractable_from: title
    known_values: ["CROCS", "HUGO BOSS", "Adidas", "Anta", "UGG", "Nike", "Puma", "Skechers", "Birkenstock", "Vans"]
    extraction: "title 中匹配 known_values（大小写不敏感）"
  - name: platform
    values: ["JD", "TMALL"]
    note: "ROSE 数据源 URL 含 jd.com 和 taobao.com"

metrics:
  - name: avg_price
    aggregation: avg
    source_column: ump_price
  - name: brand_count
    aggregation: count_distinct
    source_column: brand

example_questions:
  - "10个品牌的价格排名？"
  - "哪个品牌价格波动最大？"
  - "CROCS在10品牌中的价格分位？"
```

### 3.5 实体注册表（跨源聚合）

```yaml
# references/semantic/entities.yml
# 跨数据源的实体别名归一化
entities:
  - name: brand
    aliases: [品牌, brand_name]
    values:
      CROCS: [CROCS, Crocs, 卡骆驰, crocs]
      HUGO_BOSS: [HUGO BOSS, BOSS, 雨果博斯]
      ADIDAS: [Adidas, adidas, 阿迪达斯]

  - name: platform
    aliases: [平台, channel, marketplace]
    values:
      JD: [JD, 京东, jd]
      TMALL: [TMALL, 天猫, tmall]

  - name: metric
    aliases: [指标, KPI, measure]
    types:
      - {name: price, aliases: [价格, 单价, amount], aggregation: avg}
      - {name: comment_count, aliases: [评论数, 评论量], aggregation: count}
      - {name: shop_count, aliases: [店铺数], aggregation: count_distinct}

  - name: intent
    types: [lookup, comparison, trend, ranking, sentiment, distribution]
```

## 4. Query Understanding

### 4.1 意图分类体系（适配 4 源数据）

基于 BI-Bench 8 类分类法 + 我们的舆情数据特性，适配为 **6 类**：

| Intent | 描述 | 示例 | 需要的数据源 | 分析模板 |
|---|---|---|---|---|
| **lookup** | 单一指标查询 | "CROCS在京东卖多少钱？" | JD/TMALL | `load(source).filter(brand).select(metric)` |
| **comparison** | 跨源/跨维度对比 | "京东vs天猫价格差异" | JD + TMALL | `load(2 sources).aggregate(metric).diff()` |
| **ranking** | 排名/TopN | "10品牌价格排名" | ROSE | `load(rose).group_by(brand).aggregate().sort().limit()` |
| **sentiment** | 舆情/反馈分析 | "用户对CROCS评价如何？" | CROCS CSV | `load(csv).filter(brand).analyze_comments()` |
| **distribution** | 分布/占比 | "各店铺商品数占比" | TMALL/ROSE | `load(source).group_by(shop).count().proportion()` |
| **trend** | 时间趋势 | "近3个月评论趋势" | CROCS CSV | `load(csv).group_by(time_bucket).count().sort(time)` |

### 4.2 实体提取规则

实体提取在 Agent 的 ReAct 循环中自然发生（Agent 读 system prompt 里的语义层摘要，然后调用 `explore_data_sources` Tool 确认）。不需要独立的 NER 管道。

Agent 在 Thought 步骤中隐式完成：

```
Thought: 用户问"CROCS在京东和天猫的价格差异"。
- brand: CROCS
- platforms: [JD, TMALL]  
- metric: price
- intent: comparison
- 需要加载 JD + TMALL 数据
```

### 4.3 JSON IR 分析计划

Agent 的 ReAct 循环产出隐式的 IR plan（通过 Tool 调用序列）。不需要显式 IR JSON 生成步骤——Tool 调用序列就是 IR：

```
Action: load_data(source="jd_products", filters={"brand": "CROCS"})
Observation: {"claims": [{"id": "c1", "metric": "avg_price", "value": 489.0, "source": "jd_products", "rows": [...]}]}

Action: load_data(source="tmall_products", filters={"brand": "CROCS"})
Observation: {"claims": [{"id": "c2", "metric": "avg_price", "value": 407.01, "source": "tmall_products", "rows": [...]}]}

Action: analyze(claims=["c1", "c2"], operation="compare")
Observation: {"claim_id": "c3", "diff": 81.99, "pct_diff": "20.1%", "c1": 489.0, "c2": 407.01}

Thought: JD 平均价 489.0，TMALL 407.01，差 81.99（JD 贵 20.1%）。所有数字来自 Tool claims。
Final Answer: {"summary": "...", "findings": [...], "evidence": ["c1", "c2", "c3"]}
```

## 5. BIAgentStrategy（Grounding System Prompt）

### 5.1 框架注入点（已验证）

```
reasoning/react.py:161-176  ReAct._system_prompt()     ← override here
reasoning/react.py:97-101   messages = [SYSTEM, history..., USER(task)]
```

```python
# src/petfish_bi_cli/agent/strategy.py
from petfishframework.reasoning.react import ReAct

class BIAgentStrategy(ReAct):
    """ReAct with BI-specific grounding constraints."""

    def _system_prompt(self, tools: list) -> str:
        base = super()._system_prompt(tools)
        return BI_GROUNDING_PROMPT + "\n\n" + base
```

### 5.2 System Prompt 草案（7 段式）

```markdown
# Role
你是 BI 数据分析 Agent。你通过 Tool 获取数据，仅基于实际数据回答问题。
你不要使用模型训练数据中的知识来替代真实数据。

# Data Sources (Semantic Layer Summary)
以下是可查询的数据源：
- crocs_xiaohongshu: 小红书 CROCS 评论数据（2034 条评论，舆情分析用）
- jd_products: 京东 CROCS 商品列表（4 条，价格查询用）
- tmall_products: 天猫 CROCS 商品列表（1275 条，87 家店，价格/店铺分析用）
- rose_10brands: ROSE 10+品牌价格情报（2853 条，跨品牌横评用）

调用 explore_data_sources 获取完整 schema 和可用指标。

# Grounding Rules（CRITICAL）
1. 你只能使用 Tool 返回的数据。不要用模型知识编造品牌信息、价格、销量。
2. 每个 Tool 返回带 ID 的 claims（如 {"id": "c42", "value": 245.3}）。
3. 你的输出中每个数字必须引用 claim ID。不允许出现未在 claims 中的数字。
4. 如果数据不足，明确说"数据不足"，不要编。

# Tool Use Protocol
- 每次只调用一个 Tool
- 等待 Observation 后再思考下一步
- 分析用 analyze Tool（确定性计算），不要自己在文本里算
- 最多 10 步循环

# Output Format
最终输出必须是合法 JSON，匹配 BIReport schema：
{
  "answer": "自然语言结论",
  "data": {
    "findings": [
      {"metric": "avg_price_jd", "value": 489.0, "claim_id": "c1"},
      {"metric": "avg_price_tmall", "value": 407.01, "claim_id": "c2"}
    ]
  },
  "status": "ok"
}

# Handling Ambiguity
- 如果问题涉及的数据源不明确，调用 explore_data_sources 查看可用数据
- 如果指标在数据源中不存在，返回 status: "no_data" 并说明缺什么
- 如果时间范围不明确，用数据中实际覆盖的时间范围

# Current Date
{current_date}
```

### 5.3 Few-Shot 示例（注入方式）

Few-shot 示例存储在 `src/petfish_bi_cli/prompts/few_shot/` 下，按意图分类。在 `BIAgentStrategy._system_prompt()` 中根据 query 类型动态注入 1-2 个示例。

```python
# src/petfish_bi_cli/prompts/few_shot/comparison.txt
# 示例：京东 vs 天猫价格对比

User: CROCS 在京东和天猫的价格差异
Thought: 需要 JD 和 TMALL 的 CROCS 价格数据
Action: load_data(source="jd_products", filters={"brand": "CROCS"})
Observation: {"claims": [{"id": "c1", "metric": "avg_price", "value": 489.0}]}
Thought: JD 均价 489.0。现在需要 TMALL 数据
Action: load_data(source="tmall_products", filters={"brand": "CROCS"})
Observation: {"claims": [{"id": "c2", "metric": "avg_price", "value": 407.01}]}
Thought: TMALL 均价 407.01。现在做对比
Action: analyze(operation="compare", claims=["c1", "c2"])
Observation: {"claim_id": "c3", "diff": 81.99, "pct": "20.1%", "jd_higher": true}
Thought: JD 比 TMALL 贵 81.99 元（20.1%）。所有数字有 claim 支撑。
Final Answer: {"answer": "CROCS在京东均价489.0元，天猫407.01元，京东贵20.1%", "data": {"findings": [{"metric": "jd_avg_price", "value": 489.0, "claim_id": "c1"}, {"metric": "tmall_avg_price", "value": 407.01, "claim_id": "c2"}, {"metric": "price_diff", "value": 81.99, "claim_id": "c3"}]}, "status": "ok"}
```

## 6. Grounding by Construction

### 6.1 ClaimsLedger 设计

Tool 不返回 raw data，返回**带 ID 的 claims**：

```python
@dataclass(frozen=True)
class Claim:
    id: str               # "c42"，全局唯一
    metric: str           # "avg_price"
    value: float | str    # 245.3 或 "positive"
    source: str           # "jd_products"
    source_rows: tuple    # 支撑此 claim 的原始行 ID
    computation: str      # "AVG(calculatedFinalPrice) WHERE brand=CROCS"

@dataclass(frozen=True)
class ClaimsLedger:
    claims: tuple[Claim, ...]
    metadata: dict        # row_count, columns, stats, warnings
```

### 6.2 Tool 输出格式（metadata not raw data）

```python
# ❌ 错误：返回原始记录给 LLM
ToolResult(value=df.to_dict())  # LLM 能编任何数字

# ✅ 正确：返回 claims + metadata
ToolResult(value={
    "claims": [
        {"id": "c1", "metric": "avg_price", "value": 489.0, "rows": ["sku1", "sku2"]},
        {"id": "c2", "metric": "min_price", "value": 359.0, "rows": ["sku3"]},
    ],
    "metadata": {
        "source": "jd_products",
        "row_count": 4,
        "columns": ["skuName", "originalPrice", "calculatedFinalPrice"],
        "stats": {"price": {"min": 359, "max": 559, "mean": 489}},
    }
})
```

### 6.3 OutputValidator

在 `BIApplication.execute()` 中，`run_structured()` 返回 `StructuredResult` 后，做 grounding 校验：

```python
class OutputValidator:
    def validate(self, report: BIReport, claims: ClaimsLedger) -> ValidationResult:
        errors = []

        # 1. 每个 finding 的 value 必须在 claims 中存在
        claim_values = {c.id: c.value for c in claims.claims}
        for finding in report.data.get("findings", []):
            cid = finding.get("claim_id")
            if cid and cid in claim_values:
                if finding["value"] != claim_values[cid]:
                    errors.append(f"Claim {cid}: value mismatch (report={finding['value']}, claim={claim_values[cid]})")
            elif finding.get("value") is not None:
                # 数字不在任何 claim 中 → T5 hallucination
                errors.append(f"Unverified value: {finding['value']} (no claim_id)")

        # 2. answer 文本中的数字必须出现在某个 claim value 中
        import re
        numbers_in_answer = re.findall(r'\d+\.?\d*', report.answer)
        all_claim_values = [str(c.value) for c in claims.claims]
        for num in numbers_in_answer:
            if not any(num in cv for cv in all_claim_values):
                errors.append(f"Number '{num}' in answer not found in any claim")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 6.3.1 ClaimsLedger 数据流（Momus 审查补充）

**问题**：`agent.run_structured()` 返回 `StructuredResult[BIReport]`，只含解析后的 report。Tool 执行期间产生的 ClaimsLedger 存在于 ReAct trajectory 的 observation 字符串中，但 `StructuredResult` 不携带结构化 claims。`OutputValidator.validate(report, claims)` 的 `claims` 参数从哪来？

**方案**：Tool 通过 DI 持有共享 `ClaimsRegistry` 引用，`execute()` 时写入。不修改框架。

```python
class ClaimsRegistry:
    """进程内 claims 收集器，BIApplication 创建并注入到每个 Tool。"""
    def __init__(self):
        self._claims: list[Claim] = []
    def add(self, claim: Claim) -> None:
        self._claims.append(claim)
    def to_ledger(self) -> ClaimsLedger:
        return ClaimsLedger(claims=tuple(self._claims), metadata={})

class LoadDataTool:
    """Tool 持有 registry 引用，execute() 时写入。"""
    def __init__(self, data_root: Path, registry: ClaimsRegistry):
        self._data_root = data_root
        self._registry = registry  # DI 注入

    def execute(self, args: dict) -> ToolResult:
        records = _ingest(args["source"], self._data_root, args.get("filters"))
        claims = _records_to_claims(records)  # 每条记录 → Claim
        for c in claims:
            self._registry.add(c)             # 写入共享 registry
        return ToolResult(value=_claims_to_metadata(claims))  # 返回 metadata 给 LLM

class BIApplication:
    def execute(self, query: BIQuery) -> BIReport:
        registry = ClaimsRegistry()           # 每次查询新建
        agent = self._make_agent(registry)    # 注入到 Tools
        result = agent.run_structured(Task(prompt=query.prompt), BIReport)
        if result.data is None:
            return BIReport(status="parse_error", answer=result.answer)
        validation = self._validator.validate(result.data, registry.to_ledger())
        if not validation.valid:
            return BIReport(status="validation_failed", answer=result.answer,
                            data={"errors": validation.errors})
        return result.data
```

**关键**：Agent 每次 `execute()` 新建 registry（非共享），与 ADR-006（Session 每请求独立）一致。FakeModel 测试时 registry 仍正常工作——Tool 的 `execute()` 照常写入 registry。

### 6.4 T1-T5 Truth Labeling（可选，M-1 后期）

每个 finding 标注 truth level：

| Label | 含义 | 示例 |
|---|---|---|
| T1_verified | 来自 Tool claim | `"value": 489.0, "claim_id": "c1"` → T1 |
| T2_computed | 由 analyze Tool 确定性计算 | `"value": 81.99, "claim_id": "c3"` → T2 |
| T3_inferred | LLM 分析推断（标注为推断） | `"text": "JD定价策略更高端", "truth": "T3"` |
| T4_refused | 数据不足，拒绝回答 | `"status": "no_data"` → T4 |
| T5_hallucination | 编造（**校验器拒绝**） | 无 claim_id 的数字 → T5 → FAIL |

## 7. 架构决策记录

### ADR-011: BI Query Framework — 意图分类 → IR → 确定性执行

**决策**：查询理解通过 Agent 的 ReAct 循环隐式完成，不需要独立 pre-processing。Agent 调用 `explore_data_sources` / `load_data` / `analyze` Tools，Tool 调用序列即为 IR plan。

**理由**：petfishframework 的 ReAct 循环天然支持多步推理。把查询理解拆成独立步骤会增加管道复杂度且失去 Agent 的自适应能力。Atlas/WrenAI 用独立步骤是因为他们面向 SQL 生成（需要 schema linking）；我们面向 CSV/JSON（Tool 直接加载）。

**后果**：system prompt 必须包含语义层摘要（数据源 + 实体 + 指标），让 Agent 知道有哪些 Tool 和数据可用。

### ADR-012: Grounding by Construction — LLM 看 metadata 不看 raw data

**决策**：所有 Tool 的 `execute()` 返回 `ClaimsLedger`（带 ID 的 claims + 统计 metadata），不返回原始记录。LLM 只能引用 claim ID。

**理由**：TRACE / StatGuard 研究证明，让 LLM 看到 raw data 是幻觉的主要来源。从结构上限制 LLM 只看 metadata + claim IDs，比靠 prompt"不要编"有效 10 倍。

**后果**：Tool 层需要确定性计算逻辑（pandas/DuckDB），不能简单返回 CSV 行。`AnalysisTool` 是确定性计算引擎，不是 LLM 生成代码。

### ADR-013: Output Validation — Substring + Number Matching

**决策**：`OutputValidator` 在 `BIApplication.execute()` 中运行。校验：每个 finding 的 value 必须匹配某 claim 的 value；answer 文本中的数字必须出现在某 claim value 中。不匹配 = T5 hallucination = 返回 `BIReport(status="validation_failed")`。

**理由**：Harbor Legal 案例——grounding 校验把 unsupported claims 从 41% 降到 3.1%。这是发布前的最后一道防线。

**后果**：少数合法推断会被误判为 T5（如 LLM 计算的百分比但未调 analyze Tool）。解决：要求 LLM 对所有计算调用 analyze Tool，不自己算。

### ADR-014: Semantic Layer — YAML 元数据，每源一个文件

**决策**：`references/semantic/*.yml` 存储每数据源的 schema、实体、指标、示例问题。Agent 通过 `explore_data_sources` Tool 读取。

**理由**：Atlas/WrenAI 的生产实践。YAML 可 diff、可版本化、Agent 可消费。比 JSON 更适合人类编辑。`sample_values` 字段锚定 LLM 对真实数据的理解。

**后果**：新增数据源 = 新增一个 YAML 文件 + 一个 ingestion adapter。语义层与 ingestion 解耦（YAML 描述"有什么"，adapter 处理"怎么读"）。

### ADR-015: BIAgentStrategy — Subclass ReAct.\_system\_prompt()

**决策**：创建 `BIAgentStrategy(ReAct)` 子类，override `_system_prompt()` 方法，注入 BI grounding 规则 + 语义层摘要 + few-shot 示例。

**理由**：explore agent 验证了 `reasoning/react.py:161-176` 是唯一的 system prompt 注入点。subclass 保持 ReAct loop + Budget + Event audit + Permission 完整，只改 prompt 文本。

**后果**：框架升级时（v0.2+），如果 `_system_prompt()` 签名变了，只需改一个方法。适配层集中在 `strategy.py`。

**已知风险**：Anthropic adapter（`anthropic.py:145-156`）在 v0.1.4 丢弃 tool descriptions。如果用 Claude，Tool 描述要在 system prompt 中显式重复。

## 8. 目录结构（新增）

```text
src/petfish_bi_cli/
├── agent/
│   ├── strategy.py              # BIAgentStrategy(ReAct)（ADR-015）
│   └── tools/
│       ├── explore.py           # explore_data_sources Tool（读语义层）
│       ├── load.py              # load_data Tool（返回 ClaimsLedger）
│       ├── analyze.py           # analyze Tool（确定性计算）
│       └── validate.py          # validate_output Tool（grounding check）
├── grounding/
│   ├── claims.py                # Claim + ClaimsLedger dataclass（ADR-012）
│   └── validator.py             # OutputValidator（ADR-013）
├── prompts/
│   ├── system_prompt.md         # BI grounding prompt 草案（§5.2）
│   ├── few_shot/
│   │   ├── comparison.txt
│   │   ├── lookup.txt
│   │   ├── sentiment.txt
│   │   └── ranking.txt
│   └── tests/
│       ├── golden_cases.json    # 回归测试用例
│       └── test_prompt_regression.py

references/semantic/              # YAML 语义层（ADR-014）
├── entities.yml                 # 跨源实体注册表
├── crocs_xiaohongshu.yml
├── jd_products.yml
├── tmall_products.yml
└── rose_10brands.yml
```

## 9. 与现有架构的集成

| 现有组件 | 集成方式 |
|---|---|
| `BIApplication.execute()`（ADR-004） | 在 `run_structured()` 后增加 `OutputValidator.validate()` |
| `BIReport` dataclass（ADR-009） | 增加 `findings[].claim_id` 字段；`status` 新增 `"validation_failed"` |
| `framework.py`（ADR-008） | `make_bi_agent()` 中 `reasoning=BIAgentStrategy()` 替代 `ReAct()` |
| `Tool` Protocol（ADR-005） | Tool `execute()` 返回 ClaimsLedger 格式 |
| FakeModel（TDD） | FakeModel 配置为输出带 claim_id 的 BIReport，验证 grounding 校验路径 |
