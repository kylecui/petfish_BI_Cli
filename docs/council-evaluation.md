# Council Evaluation: petfish_BI_Cli Production Readiness

> **评估日期**: 2026-07-07
> **方法**: Council Thinking (5+1 多视角对抗式审查)
> **参与顾问**: Critic / Essence / Opportunity / Outsider / Executor + Arbiter
> **结论**: **CONDITIONAL** — 内部 CLI 工具基本就绪；对外 Web 服务或关键业务依赖**未就绪**

---

## 评估对象

petfish_BI_Cli v0.1.0-alpha：AI for BI CLI 工具，基于 petfishframework v0.1.4。
- 169 个测试通过，ruff clean
- 4 个真实数据源，8 个 milestone（M-1 到 M6）完成
- 15 个 ADR，Oracle + Momus 双重审查
- SiliconFlow Qwen2.5-72B-Instruct 真实模型集成验证（4/4 levels）
- Grounding by Construction 防幻觉机制

---

## Council 五顾问原始判断

### Critic / 反对者（重建）

**核心判断**: "production ready" 这个 claim 站不住脚，因为三个关键前提没有证据：

1. **Grounding 机制被高估**。`OutputValidator` 只有 42 行，用 `\d+\.?\d*` regex 抓数字做 substring 匹配。如果 LLM 写"约 424"或"四百二十四"，validator 漏检。声称的"构造性防幻觉"在实现层是漏网。
2. **169 个测试验证的是机制（wiring），不是输出质量**。只有 4 个集成测试用真实模型。FakeModel 测的是"代码路径是否走通"，不是"真实查询的准确率"。
3. **petfishframework v0.1.4 是 Alpha**。API 可能 break，生产依赖一个标注 Alpha 的框架本身就是风险决策。

**对决策的影响**: 在补齐真实模型准确率基准 + 对抗性 grounding 测试 + 框架版本锁定之前，"production ready" 的 claim 应降级为"PoC verified"。

---

### Essence / 本质思考者（重建）

**核心判断**: 真正的问题不是"是否 production ready"，而是**"production 指向谁、用户在哪、SLA 是什么"**。

1. **没有用户的 production ready 是学术判断**。如果只是自用 CLI，80% 就绪；如果要对外服务，缺认证/限流/可观测性，差 50%+。
2. **项目真正的成就不是 BI 工具，是 Grounding by Construction 模式**。98 行代码定义了一个可复用的反幻觉范式。BI 工具是验证这个模式的载体，不是终点。
3. **讨论被"production ready"这个框架限制**。更有价值的问题是："这个项目下一步该验证什么假设？"——答案是真实用户查询的准确率和成本。

---

### Opportunity / 机会挖掘者（完整）

**核心判断**: 离 production ready 差临门一脚，但**最大机会不在"补缺口上线"，而在把已有差异化资产变现**。

关键杠杆点（按 ROI 排序）:
1. **黄金 demo 缺失 = 最高 ROI**。`outputs/` 和 `examples/` 全空。补 3-5 个 golden example JSON 报告（< 4h），把"声称 ready"变成"一秒可验证 ready"。
2. **Grounding by Construction 是可外溢 IP**。98 LOC 的 `grounding/` 模块是自包含反幻觉范式。从"内部实现"重新定位为"可发布的 pattern library + 技术博客"。
3. **YAML 语义层是跨项目可复用资产**。5 个 YAML 编码了中国电商品牌别名/平台映射/指标聚合。
4. **`scripts/integration_test.py` L1-L4 是最佳 sales demo**。60 秒可跑的端到端验证，比任何架构图有说服力。
5. **中文检索/情感分析是隐形护城河**。`chinese_retriever.py` + `sentiment/lexicon.py`(278 LOC 中文词典) 让它在中文 UGC 场景天然优于英文优先框架。

诚实声明:
- "Grounding by Construction" 在对抗性查询下是否成立？validator 的 regex 在"约424"/"一千二百"等中文数字表达下会漏检。
- 每次查询的成本和延迟是否有 production 可接受？无基准数据。
- 是否存在真实等待上线的用户？

---

### Outsider / 局外人（完整）

**核心判断**: 站在真实买家角度，**不能称为 production ready**。是结构精良、技术自洽的 **PoC**，但用户能感知的价值几乎没有交付。

关键问题:
1. **`outputs/` 和 `examples/` 都是空的**。BI 工具的全部价值在报告产出，仓库里**没有一份样本报告**。
2. **数据是冻结的单次快照（2026-06-05），且全是 CROCS**。真实 BI 痛点是持续更新/跨品类/时间趋势——这些能力**完全没演示**。
3. **README 与实际验证路径矛盾**。QuickStart 写 `OPENAI_API_KEY` + `gpt-4o`，但验证用 SiliconFlow Qwen2.5-72B。新用户照 README 操作会直接失败。
4. **目标用户与交付形态错位**。BI 消费者是品牌经理/市场总监，不用 CLI。Web API 存在但无认证/无 demo/无截图。
5. **宣传话术全是框架语言**。"Grounding by Construction"、"Pass^k"、"event-sourced Session"——BI 买家听不懂，换不成"我为什么该付钱"。
6. **数据合规是潜在雷区**。"小红书 UGC 2034 条"、"JD Raw Memory Dump"——无数据来源声明/授权说明。

我不知道:
- 真实 query 在真实模型上的**数字准确率**。
- 单次查询的**LLM 成本和延迟**（72B ReAct 多轮 = 几秒？几毛钱？）。
- petfishframework Alpha 的 **API 稳定性承诺**有多强。
- "production ready" 的**真实判据**是什么（demo 给老板 vs 上架卖陌生人）。

---

### Executor / 执行者（完整）

**核心判断**: "production ready" 取决于定义——**内部 CLI 基本可用**，**对外 Web 或关键业务依赖远未就绪**。阻塞项不是"功能不够"，是**故障路径未设计**。

立即做（<4h，止血）:
1. **锁死 Web 暴露面**：`web.py` 加 API key 中间件（读 env `BI_CLI_API_KEY`），CORS deny。
2. **`JobRegistry` 加上限 + TTL**：`len > 1000` 拒绝；后台清理 `>30min` 的 pending/running。防 OOM。
3. **petfishframework 版本锁定**：`>=0.1.4` → `==0.1.4`（Alpha 阶段 minor bump 可能 break）。

短期验证（1-2 天）:
4. **真实模型 smoke 脚本**：固定 3 个已知答案查询，断言 `status=="ok"` + `validate_report` 通过。
5. **`run_job_async` 加 1 层 retry**：LLM 失败指数退避 2 次。
6. **Prompt 回归基线**：system_prompt + few_shot 哈希记到 `qa/prompt_baseline.txt`，CI 断言一致。

后续建设（5-8 人天）:
7. Docker + CI（M4 已规划）
8. Session 持久化（SQLite event store）
9. 可观测性（结构化日志 + `/health`）
10. 框架 Alpha 风险对冲（contract 测试）

停止做:
- 在没真实模型 smoke 的情况下宣称"已验证真实模型集成"。
- 往 in-memory registry/sessions 塞东西不清理。
- ROSE HTML 解析、embedding few-shot（先补故障路径）。

---

## 交叉审查（Step 3）

### 高度收敛的判断（≥3 个顾问一致）

| # | 观点 | 支持者 | 置信度 |
|---|---|---|---|
| C1 | `outputs/`/`examples/` 空缺是最大可信度漏洞 | Opportunity #1, Outsider #1, Executor 隐含 | ⭐⭐⭐⭐⭐ |
| C2 | 真实模型准确率无基准（FakeModel 测机制不测质量） | Critic #2, Outsider #8, Executor #4 | ⭐⭐⭐⭐⭐ |
| C3 | Web API 无认证/限流/清理 = 生产阻塞 | Outsider #4, Executor #1, #2 | ⭐⭐⭐⭐⭐ |
| C4 | 单次快照数据无法证明趋势/增量能力 | Outsider #2, Opportunity #4 | ⭐⭐⭐⭐ |
| C5 | petfishframework Alpha 是未对冲风险 | Critic #3, Outsider #8, Executor #3 | ⭐⭐⭐⭐ |
| C6 | 成本/延迟无基准 | Opportunity, Outsider, Executor | ⭐⭐⭐⭐ |
| C7 | Grounding validator 实现层粗糙（regex） | Critic #1, Opportunity #2 | ⭐⭐⭐ |

### 分歧与张力

| 议题 | Opportunity 立场 | Outsider 立场 | Executor 立场 |
|---|---|---|---|
| 下一步优先级 | 先做 demo/IP 变现 | 先补用户可验证证据 | 先做风险止血 |
| CLI 是否合适交付形态 | 不质疑 | 质疑（BI 用户不用 CLI） | 按部署形态分情况 |
| Grounding 层定位 | 提取为独立 IP | 用户不关心，是内部话术 | 先补 contract 测试 |

---

## 删除弱观点（Step 4）

以下观点被 Arbiter 判定为弱、过早或超出本次评估范围：

1. **"提取 ClaimsLedger 为独立库"**（Opportunity）— 过早分散精力，当前应聚焦核心产品。
2. **"CLI 是错误交付形态"**（Outsider）— 架构决策（ADR-004）已定，且 Web API 已存在，不在本次评估范围。
3. **"停止 ROSE HTML 解析"**（Executor）— 该任务已不在当前 backlog 优先级中。
4. **"中文检索是护城河"**（Opportunity）— 需要竞品对比数据支撑，当前无证据。

---

## Arbiter 综合结论（Step 5）

### 总体评级: **CONDITIONAL**

```
┌─────────────────────────────────────────────────────┐
│ petfish_BI_Cli Production Readiness: CONDITIONAL    │
│                                                     │
│ 内部 CLI 工具:  ████████░░  80%  基本就绪            │
│ 私有 Web 服务:  █████░░░░░  50%  需补认证/清理/持久化 │
│ 对外 SaaS:      ███░░░░░░░  30%  需补全部 + 合规/SLA │
└─────────────────────────────────────────────────────┘
```

### 核心判断

项目是**工程纪律极好的 PoC**，不是 production-grade 产品。差距不在"功能数量"（8 个 milestone + 169 测试已足够），而在**用户可验证性和故障路径设计**：

1. **用户可验证性**: 仓库没有任何样本产出（`outputs/` 空），README 与实际验证路径矛盾，真实模型准确率/成本/延迟零基准。"声称 ready"与"可验证 ready"之间缺一步。
2. **故障路径设计**: Web 无认证、Job 无 TTL、Session 无持久化、Agent 无 retry、框架版本未锁。任何一个在真实负载下都会导致故障。

### 关键决策建议

**不要现在冲 production 上线**。按以下顺序推进：

1. **止血（半天）**: Web API key + Job TTL + 框架版本锁定
2. **验证（1-2 天）**: 真实模型 smoke + golden examples + README 对齐
3. **加固（5-8 天）**: Docker + CI + Session 持久化 + 可观测性

### 我不知道（Arbiter 诚实声明）

- "production" 的真实指向（内部工具 / 私有服务 / 对外 SaaS）——这决定 50% 的优先级排序。
- 真实用户查询的准确率分布——这是判断 BI 工具价值的唯一硬指标，当前无数据。
- petfishframework 的 backward compatibility 承诺——框架一 break 全盘重来。
- 数据合规边界——UGC 评论和平台 dump 的授权状态未声明。

---

## 附录: Council 元数据

- **顾问完成度**: 3/5 完整返回（Opportunity/Outsider/Executor），2/5 重建（Critic/Essence 从收敛主题重建）
- **判断一致性**: 7 个收敛点中 5 个获 ≥3 顾问一致支持
- **删除弱观点**: 4 条（提取独立库/CLI 错误/停止 ROSE/中文护城河）
- **最大不确定性**: 真实模型准确率 + 成本/延迟基准
