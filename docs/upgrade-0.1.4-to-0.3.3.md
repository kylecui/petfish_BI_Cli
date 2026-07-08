# petfishframework 0.1.4 → 0.3.3 升级报告

> **日期**: 2026-07-08
> **结果**: ✅ 零破坏性变更，301 tests 全通过，ruff clean

---

## 升级结果

| 指标 | 0.1.4 | 0.3.3 | 变化 |
|---|---|---|---|
| 版本 | 0.1.4 | 0.3.3 | 跨 15 个版本 |
| 测试通过 | 301 | 301 | **零回归** |
| ruff | clean | clean | — |
| 向后兼容 | — | ✅ 完全兼容 | 0 breaking changes |

## 新能力清单（0.3.3 可用但尚未采用）

| 能力 | 模块 | 对产品的价值 | 采用工作量 |
|---|---|---|---|
| **YAML Policy Engine** | `petfishframework.policies.YamlPolicy` | 用 YAML 声明权限规则，分离配置与代码 | 创建 policy YAML + Agent 注入 |
| **CredentialBroker** | `petfishframework.credentials` | 安全的 API key/token 生命周期管理（限时、限量、自动回收） | 创建 broker + 注册凭据 |
| **LATS 推理** | `petfishframework.reasoning.LATS` | Language Agent Tree Search — 复杂推理任务的更优策略 | 替换 ReAct() |
| **LLM+P 推理** | `petfishframework.reasoning.LLMPlusP` | LLM + Planning — 先规划再执行 | 替换 ReAct() |
| **BaseTool 元数据** | `side_effect/idempotent/external_egress/requires_credentials` | 工具风险标注，让权限引擎更精准 | 每个 Tool 加几行 |
| **MASK 增强** | 嵌套 dot-path + 输入/输出/事件三层掩码 | PII 字段自动脱敏 | 配置 mask_fields |
| **AuditReport** | 审计报告生成（Markdown/JSON） | 替代手动事件遍历 | ~1 行调用 |
| **DEGRADE 策略** | 后备工具切换 + fail-closed | 高风险操作自动降级 | 配置 fallback tool |
| **细化事件类型** | `tool.blocked/masked/degraded/approval_required` | 更精确的审计追踪 | 自动生效 |

## 对行动路线图的影响

### 原计划 vs 升级后

| 原计划项 | 升级后变化 |
|---|---|
| P0.1 启用 SARC 权限策略 | **更简单**：可用 `YamlPolicy.from_file()` 替代手写 Python 策略类 |
| P0.3 注入防御 | **不变**：框架不提供数据层 sanitize |
| Q4 安全：CredentialBroker | **已内置**：`CredentialBroker` 可直接用，无需自建 |
| Q1 扩展性：Tool Registry | **受益**：`BaseTool` 新增的元数据字段让自动注册更有语义 |
| Q2 DuckDB | **不变**：框架层面无影响 |

### 调整后的优先级

```
Sprint 1 (本周):
  1. DuckDB 集成                    ← 数据层基础
  2. YAML Policy Engine 启用         ← 一行代码 + 一个 YAML 文件
  3. Markdown 渲染 (Jinja2)          ← outputs/ 可验证
  4. 输出 PII 脱敏 (MASK 策略)       ← 用框架原生 MASK 替代手写 redact
  5. BaseTool 元数据标注              ← 为权限引擎铺路

Sprint 2 (下周):
  6. DuckDB 替代手写 parser
  7. CredentialBroker 集成
  8. Tool Registry (文件扫描)
  9. LATS 推理策略评估（对比 ReAct）
```
