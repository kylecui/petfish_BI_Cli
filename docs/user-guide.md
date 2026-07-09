# petfish BI CLI 用户使用手册

## 1. 产品概述

petfish BI CLI 是一个 AI for BI 命令行工具。客户通过 CLI 或 Web API 发出自然语言咨询，系统从电商原始数据（CSV/JSON）中检索信息，执行分析，返回 JSON 报告（必须）和富文本内容（可选）。

所有数据声明、BI 脚本、输出模板、权限策略均通过 YAML 配置驱动，无需改代码。

## 2. 安装部署

### 2.1 一键安装

```bash
git clone <repo-url> petfish-bi
cd petfish-bi
./install.sh
```

`install.sh` 自动完成：检查 Python → 安装 uv → 依赖同步 → 配置初始化 → 健康检查。

### 2.2 手动安装

```bash
python3 --version              # 需要 3.10+
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra web --extra openai
cp configs/bi_cli.example.yml configs/bi_cli.yml
uv run petfish-bi health
```

### 2.3 Docker 部署

```bash
docker compose up -d
# Web API: http://localhost:8000
# Health:   http://localhost:8000/health
```

### 2.4 配置向导

```bash
petfish-bi config init
```

交互式向导自动扫描数据文件、生成 `configs/bi_cli.yml`。

## 3. 配置参考

所有配置在 `configs/bi_cli.yml`。完整模板见 `configs/bi_cli.example.yml`。

### 3.1 模型配置

```yaml
model:
  provider: openai          # openai | anthropic | fake
  name: gpt-4o              # 模型名
  api_key: null             # null = 读 OPENAI_API_KEY 环境变量
  base_url: null            # null = 读 OPENAI_BASE_URL 环境变量
  temperature: 0.0
  max_tokens: 4096
```

设置 API Key：

```bash
export OPENAI_API_KEY="sk-..."
# 或 SiliconFlow:
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
```

`provider: fake` 使用 FakeModel，无需 API Key，用于测试。

### 3.2 数据源声明

将数据文件放入 `references/` 目录，在配置中声明：

```yaml
sources:
  jd_products:
    type: json                          # json | csv | jsonl
    path: jd/JD_CROCS_Raw_Memory_Dump.json
    description: "京东商品列表"
    schema:
      json_path: "raw_data.search_results[]"   # JSON dot-path（可选）
    metrics:
      - name: avg_price
        column: calculatedFinalPrice
        aggregation: avg               # avg | min | max | count | sum
        unit: CNY
        aliases: ["均价"]               # Agent 识别的中文别名
      - name: product_count
        aggregation: count
    entities:
      - name: brand
        values: ["CROCS"]
        source_column: skuName
```

`metrics` 可选——省略时系统尝试自动检测数值列。

配置 `sources:` 后，Agent 自动感知新数据源。调用 `explore_data_sources` 工具列出所有可用源。

### 3.3 BI 脚本接入

将客户既有的 Python/Shell/SQL 脚本包装为 Agent 可调用的工具：

```yaml
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
    timeout_s: 30                       # 超时秒数（最大 300）
    risk_level: medium                  # low | medium | high
    capabilities: ["data:read"]
    sandbox_env: true                   # 过滤环境变量，仅保留 PATH/HOME/USER
```

脚本执行机制：
- 输入参数通过 stdin 以 JSON 传入
- stdout 输出（JSON 格式时自动解析 + 注册 Claim）
- 非零退出码或超时返回错误
- 默认 `side_effect: true`，权限策略默认拒绝（需显式允许）
- `sandbox_env: true` 时，脚本仅能访问 PATH/HOME/USER/LANG 环境变量，API Key 等敏感信息不会泄露到客户脚本

权限策略中添加允许规则：

```yaml
# configs/policy.yml
rules:
  - name: "allow-sales-report"
    priority: 250
    when:
      tool.name: "run_sales_report"
    effect: ALLOW
    reason: "Explicit allow for sales_report script"
```

### 3.4 输出模板

自定义 JSON / Markdown / HTML 输出格式：

```yaml
templates:
  default:
    json: templates/report.json.j2
    markdown: templates/report.md.j2
    html: templates/report.html.j2
```

模板使用 Jinja2 语法，可用变量：
- `report.answer` — Agent 自然语言回答
- `report.data.findings` — 结构化发现（含 value、claim_id）
- `report.session_id` — 会话 ID
- `claims` — ClaimsLedger（引用来源）

省略 `templates:` 时使用内置默认模板。

### 3.5 权限策略

```yaml
# configs/policy.yml
version: "1.0"
name: "bi-cli-default"

rules:
  - name: "deny-write-tools"
    priority: 200
    when:
      tool.side_effect: true
    effect: DENY

  - name: "deny-external-egress"
    priority: 200
    when:
      tool.external_egress: true
    effect: DENY

  - name: "redact-audit-filters"
    priority: 150
    when:
      tool.capabilities_contains: "data:read"
    effect: ALLOW
    event_mask_fields:
      - args.filters

  - name: "allow-read-tools"
    priority: 100
    when:
      tool.capabilities_contains: "data:read"
    effect: ALLOW

  - name: "default-allow"
    priority: 0
    when: {}
    effect: ALLOW
```

### 3.6 RAG 配置

```yaml
rag:
  enabled: true
  retriever: crag             # simple | crag
  chunk_size: 500
  top_k: 5
  documents:
    - path: docs/brand-guide.md
    - path: references/spec.pdf
      type: pdf
```

启用后 Agent 自动挂载 CRAGRetriever，在回答前检索文档库。

### 3.7 Vault 密钥管理（可选）

```yaml
vault:
  enabled: true
  url: https://vault.example.com
  token: null                  # null = 读 VAULT_TOKEN 环境变量
  api_key_path: secret/data/bi-cli/openai-key
```

安装：`uv sync --extra vault`

### 3.8 预算控制

```yaml
budget:
  max_tokens_per_session: 100000
  max_cost_usd: 0.50
  max_steps: 25
```

### 3.9 推理策略

Agent 默认使用 ReAct（推理+行动）策略。可选启用 Reflexion 自反思模式：

```yaml
reasoning:
  reflexion: true            # 启用自反思重试
  max_reflections: 2         # 最大反思轮次（默认 2）
```

启用后，Agent 在回答不理想时自动：
1. 反思上次尝试失败的原因
2. 生成"经验教训"
3. 带着教训重试
4. 最多重试 `max_reflections` 次，取最优结果

适用场景：复杂对比分析、多步骤推理、首次回答 validation_failed 时。

### 3.10 熔断保护

模型 API（SiliconFlow/OpenAI）连续失败时自动触发熔断，避免雪崩：

```yaml
# 在 model_factory 中自动生效，无需配置
# 默认参数：连续 5 次失败 → 开路 → 冷却 60s → 半开试探
```

熔断状态：
- **CLOSED**（正常）→ 调用通过
- **OPEN**（熔断）→ 直接拒绝调用，不消耗 Token
- **HALF_OPEN**（试探）→ 允许一次调用，成功则恢复 CLOSED

适用场景：SiliconFlow 限流、OpenAI 服务波动、网络抖动。

## 4. CLI 参考

### 4.1 ask — 查询

```bash
petfish-bi ask "CROCS在京东的均价是多少？"
petfish-bi ask "京东和天猫的价格差异" --output report.json
petfish-bi ask "小红书CROCS评论情感分析" --data-source crocs_xiaohongshu
```

返回 JSON 报告：

```json
{
  "answer": "CROCS在京东的平均价格为561.01元。",
  "data": {
    "findings": [
      {"metric": "avg_price_jd", "value": 561.01, "claim_id": "c1"}
    ]
  },
  "session_id": "abc123",
  "status": "ok"
}
```

`status` 取值：
- `ok` — 查询成功，数据已验证
- `validation_failed` — 回答中有数字未在 Claim 中找到
- `parse_error` — Agent 返回无法解析
- `budget_exceeded` — Token/费用超限
- `no_data` — 数据源中没有匹配数据

### 4.2 sources — 列出数据源

```bash
petfish-bi sources
```

输出所有已配置的数据源及其类型和描述。

### 4.3 health — 健康检查

```bash
petfish-bi health
```

检查配置有效性、数据目录是否存在、模型适配器是否可用。退出码 0 = 健康。

### 4.4 web — 启动 Web API

```bash
petfish-bi web --port 8000
petfish-bi web --host 0.0.0.0 --port 8080
petfish-bi web --no-hot-reload-policy    # 禁用策略热重载
```

Web 启动时自动：
- 挂载 PolicyHotReloader 监视 `configs/policy.yml`（修改后自动重载，无需重启）
- 初始化 ConversationStore（支持 `/chat` 多轮对话）

### 4.5 config — 配置管理

```bash
petfish-bi config init      # 交互式生成配置
petfish-bi config show      # 查看当前配置摘要
```

## 5. Web API 参考

### 5.1 POST /analyze

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "CROCS在京东的均价是多少？"}'
```

返回 JSON 报告（同 CLI `ask` 命令）。

### 5.2 POST /chat — 多轮对话

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "CROCS京东均价", "conversation_id": "conv-001"}'
```

响应：

```json
{
  "conversation_id": "conv-001",
  "answer": "CROCS在京东的平均价格为561.01元。",
  "data": {"findings": [{"metric": "avg_price_jd", "value": 561.01}]},
  "status": "ok"
}
```

`conversation_id` 可省略（自动生成）。同一 `conversation_id` 的多次调用构成一个对话会话。

### 5.3 GET /health

```bash
curl http://localhost:8000/health
```

### 5.4 GET /sources

```bash
curl http://localhost:8000/sources
```

### 5.5 GET /jobs/{job_id}

```bash
curl http://localhost:8000/jobs/abc123
```

查询异步 `/analyze` 任务的结果。

## 6. 数据源接入指南

### 6.1 CSV 文件

```yaml
sources:
  my_csv:
    type: csv
    path: my_data.csv
    description: "我的CSV数据"
    metrics:
      - name: avg_revenue
        column: revenue
        aggregation: avg
```

系统自动读取 CSV 表头，`column` 指定数值列名。

### 6.2 JSON 文件

```yaml
sources:
  my_json:
    type: json
    path: data.json
    description: "我的JSON数据"
    schema:
      json_path: "results.items[]"    # dot-path 到数据数组
    metrics:
      - name: avg_price
        column: price
        aggregation: avg
```

### 6.3 现有内置数据源

无需配置即可使用（通过 `references/semantic/*.yml` 自动加载）：

| Source ID | 类型 | 说明 |
|---|---|---|
| `jd_products` | JSON | 京东 CROCS 商品 |
| `tmall_products` | JSON | 天猫 CROCS 商品 |
| `crocs_xiaohongshu` | CSV | 小红书 CROCS 评论 |
| `rose_10brands` | JSON | ROSE 10 品牌数据 |

在 `bi_cli.yml` 中声明 `sources:` 后，配置声明的源优先于内置源。

## 7. Grounding 验证

系统对 Agent 回答中的每个数字进行来源验证：

1. Agent 调用 Tool → Tool 返回 Claim（含数值 + 来源）
2. Agent 生成回答 → 提取回答中所有数字
3. 验证器检查每个数字是否在 Claim 中有对应记录
4. 从已验证数字推导的值（差值、百分比）自动通过

验证失败时返回 `status: validation_failed`，回答仍可见但标记为未验证。

## 8. 审计与安全

### 8.1 审计日志

所有 Agent 事件自动记录到 `outputs/audit/siem.jsonl`：
- `session.start` — 会话开始
- `tool.called` — 工具调用（含参数 + 权限决策）
- `tool.masked` — 字段脱敏
- `tool.blocked` — 权限拒绝
- `model.called` — 模型调用
- `session.end` — 会话结束

### 8.2 PII 脱敏

自由文本字段（query、answer、reason）中的 PII 自动脱敏：
- 手机号 → `[手机号已脱敏]`
- 邮箱 → `[邮箱已脱敏]`
- 身份证 → `[身份证已脱敏]`
- 银行卡 → `[银行卡已脱敏]`

### 8.3 OTel 追踪（可选）

安装 `uv sync --extra otel` 后，Agent 事件自动发送到 OpenTelemetry。

## 9. 常见问题

### Q: Agent 返回 `validation_failed`

回答中有数字未在 Claim 中找到。检查：
1. Tool 是否正确注册了 Claim
2. 如果是推导值（差值/百分比），验证器支持自动推导
3. 查看 `outputs/audit/siem.jsonl` 中 `tool.called` 事件的 Claim 列表

### Q: `parse_error`

Agent 返回的内容不是有效 JSON。检查：
1. 模型是否支持 JSON 结构化输出
2. Token 预算是否足够
3. 尝试降低 `temperature` 或换用更强的模型

### Q: 脚本工具被拒绝

默认权限策略拒绝 `side_effect: true` 的工具。在 `configs/policy.yml` 中添加显式 ALLOW 规则。

### Q: 如何添加新数据源

1. 将文件放入 `references/`
2. 在 `bi_cli.yml` 的 `sources:` 中声明
3. 运行 `petfish-bi health` 验证
4. 无需重启——下次查询自动感知

### Q: 如何使用 SiliconFlow

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
```

```yaml
model:
  provider: openai
  name: Qwen/Qwen2.5-72B-Instruct
```

### Q: 熔断器触发后怎么办

模型 API 连续失败 5 次后熔断器开路，调用直接拒绝。等待 60 秒后自动进入半开状态试探恢复。如需手动恢复，重启服务即可（熔断器是进程内状态）。

### Q: Reflexion 和普通 ReAct 有什么区别

ReAct 执行一次推理链。Reflexion 在 ReAct 基础上增加"反思→重试"循环：如果首次回答不理想，Agent 会反思原因并带着经验教训重试。代价是消耗更多 Token（每次反思额外调用模型）。

### Q: 客户脚本会泄露 API Key 吗

当 `sandbox_env: true` 时，脚本只能访问 PATH/HOME/USER/LANG 环境变量。OPENAI_API_KEY、VAULT_TOKEN 等敏感变量被过滤。默认 `sandbox_env: false`（不过滤），建议对不信任的脚本启用。
