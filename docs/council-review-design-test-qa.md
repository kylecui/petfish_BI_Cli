# Council 审查：设计架构 + 测试用例 + QA/QC

> **日期**: 2026-07-08
> **方法**: Council Thinking 5+1（Critic / Essence / Opportunity / Outsider / Executor + Arbiter）
> **评估对象**: petfish_BI_Cli 的设计架构、测试用例质量、QA/QC 流程
> **结论**: **CONDITIONAL FAIL** — 架构和测试数量达标，但 QA/QC 不达标。核心交付物从未端到端验证。

---

## 1. 问题重述

真正要判断的不是"291 tests 够不够"或"12 ADR 多不多"，而是：**这套系统是否产出过哪怕一条经真人核验为真的 BI 回答？** 在回答这个问题之前，所有工程完成度数字都在测量脚手架，而非产品。

---

## 2. 五顾问原始判断摘要

### 反对者 Critic

**核心攻击**："存在但未验证"是最危险的工程反模式。Dockerfile / CI / 监控 / auth 全部写了但没跑过。291 passed 测的是 FakeModel 脚手架正确性，不是 BI 正确性。`outputs/` 空目录意味着"Grounding by Construction"是架构口号，不是已验证行为。

### 本质思考者 Essence

**核心重构**：项目花了巨大精力建造"防幻觉的结构性保证"，却至今没有产出任何一条端到端、经真人核验为真的 BI 回答。**ClaimsLedger 保证的是 provenance（出处可追溯），不保证 truthfulness（解读正确）**。模型把 raw data 解读错了，ledger 会一丝不苟地把错误也记下来。OutputValidator 只做 substring + number matching，是结构性校验伪装成语义校验。

### 机会挖掘者 Opportunity

**核心发现**：`grounding/` 不是"regex validator 弱点"，是被命名错的 **core IP**——它是 numeric provenance checking，市面上 90% 的 AI for BI 工具做不到。GOLDEN_CASES 的 schema 已设计好，是公开 benchmark 雏形。4 个异构数据源是护城河原型。但所有杠杆点都被 `outputs/` 空目录阻塞。

### 局外人 Outsider

**核心攻击**（全部有仓库内可核验证据）：
1. README Quick Start 用 OpenAI 路径，实际验证用 SiliconFlow Qwen——新人照 README 操作会直接失败
2. `outputs/` 空——零个示例 JSON 报告
3. CI 运行 `pytest -m "not integration"`——每次绿灯精确排除了唯一能证明"真模型能用"的测试
4. Dockerfile CMD 跑 uvicorn（web server），但产品定位是 CLI——部署的压根不是 README 描述的产品
5. CI 有逃生舱：`mypy src/ || true`——类型错误不阻断 CI
6. "Grounding by Construction" 在 architecture.md 里 grep 不到对外解释

### 执行者 Executor

**核心判断**：架构设计与测试数量达标，QA/QC 不达标。不要在 Validator 升级 / Session 持久化 / Prompt 回归上投入。当前瓶颈是"证明系统可用"，不是"提升系统质量"。先补交付证据。

---

## 3. 交叉审查

### 高度收敛的判断（≥4 顾问一致）

| # | 观点 | 支持者 | 置信度 |
|---|---|---|---|
| C1 | `outputs/` 空是当前唯一阻塞性问题 | 全部 5 人 | ⭐⭐⭐⭐⭐ |
| C2 | 291 tests 测的是 FakeModel 脚手架，不是 BI 正确性 | Critic, Essence, Outsider, Executor | ⭐⭐⭐⭐⭐ |
| C3 | Docker/CI "存在但未验证"产生虚假生产就绪信号 | Critic, Outsider, Executor | ⭐⭐⭐⭐ |
| C4 | README 与实际验证路径不一致，新人会卡死 | Outsider（+Essence 隐含） | ⭐⭐⭐⭐ |

### 独立高价值观点

| 顾问 | 独特贡献 | 是否改变判断路径 |
|---|---|---|
| **Essence** | ClaimsLedger 保证 provenance 不保证 truthfulness | ✅ 改变叙事：从"我们有 grounding"→"我们有 traceability 但无 verified accuracy" |
| **Outsider** | Dockerfile CMD 跑 web server，但产品是 CLI | ✅ 具体bug：部署的不是 README 描述的产品 |
| **Outsider** | CI `mypy || true` + integration 全部 deselected | ✅ 两个软门 = "CI 绿"无意义 |
| **Executor** | Golden cases 拆成 FakeModel 确定性 + 真实 API 两类 | ✅ 改变测试策略：不依赖 key 也有回归保护 |
| **Opportunity** | `grounding/` 是 numeric provenance IP，不是 regex 弱点 | ✅ 改变定位：从"BI CLI 工具"→"BI grounding IP + 工具" |

### 分歧与张力

| 议题 | Critic 立场 | Opportunity 立场 |
|---|---|---|
| Validator regex | "Grounding 承诺自打脸" | "被命名错的 core IP" |
| → Arbiter 裁定 | **两者都对**。regex 提取层是弱实现，但 Claim→Ledger→Validator 结构是强架构。问题不在 regex，在于"用 regex 结果声称语义保证"。对外沟通应降级措辞为"structured traceability"而非"semantic grounding"。 |

---

## 4. 删除弱观点

以下观点被 Arbiter 判定为弱、过早或超出本次评估范围：

1. **"Alpha 框架依赖风险"**（Critic #4）— 虽然正确，但不可操作（现在不能换框架），且所有顾问已隐含认知。删除。
2. **"bi_cli.yml multi-model roles = 企业级 packaging ready button"**（Opportunity）— 无外部用户，过早。删除。
3. **"多源 ingestion 是护城河"**（Opportunity #3）— 有趣但分散注意力。保留为长期备注，不进当前行动清单。
4. **"12 ADR 不是真 ADR"**（Outsider #6）— 形式主义批判，不改变判断。保留为改进建议，不列为 blocker。

---

## 5. Arbiter 综合结论

### 总体评级

```
┌───────────────────────────────────────────────────────┐
│           CONDITIONAL FAIL                            │
│                                                       │
│ 设计架构:     ██████████  100%  ✅ 达标               │
│ 测试覆盖:     ████████░░   80%  ⚠️ 数量达标，深度不足  │
│ QA/QC 流程:   ████░░░░░░   40%  ❌ 不达标             │
│ 产品验证:     ░░░░░░░░░░    0%  ❌ 从未端到端验证      │
└───────────────────────────────────────────────────────┘
```

### 核心判断

**设计架构达标。测试数量达标但覆盖深度不足（全部 FakeModel）。QA/QC 不达标——核心交付物（JSON report）从未端到端产出过一次。** 这不是质量问题，是**验证缺失问题**。所有工程完成度数字在 outputs/ 填上之前都是"未验证投入"。

### 最大风险

**"存在但未验证"反模式**：Dockerfile、CI、auth、monitoring 全部写了但没跑过。比"没写"更危险——它在 review 和汇报中产生虚假的生产就绪信号。更严重的是：**团队已知问题（README 错误）记录在 gap-analysis 里却仍未修**，这说明"发现问题→记录→修复"的闭环没合上。

### 最大机会

**`grounding/` 模块是 numeric provenance IP**（Opportunity 发现，Essence 重构）。市面上 90% 的 AI for BI 工具直接让 LLM 念数字，没有追溯链路。你的 Claim→Ledger→Validator 结构是差异化资产。但当前它被两个问题阻塞：
1. outputs/ 空 = 无法展示"成功长什么样"
2. 对外叙事用了"Grounding by Construction"但从未解释给外人听

### 关键叙事修正

**从 Essence 的重要重构**：

| 原叙事 | 修正后 |
|---|---|
| "Grounding by Construction 防幻觉" | "Structured traceability：每个数字可追溯到 raw data 行" |
| "291 tests passed = 质量保证" | "291 component tests passed; end-to-end BI correctness TBD" |
| "已验证真实模型集成 4/4" | "一次性手动验证通过；CI 持续验证未建立" |

---

## 6. 下一步行动

### 立即做（今天，<4h）

1. **跑一次真实端到端查询，产出 ≥1 份 sample JSON report 到 `outputs/`**
   - 用 SiliconFlow Qwen2.5-72B
   - 选 `references/` 里一个数据源（建议 jd_products，数据量小）
   - 从 CLI 输入到 JSON 输出完整跑通
   - 附上 retrieval→claim→validator 的可追溯链路标注

2. **修 README Quick Start**：把真实验证路径（SiliconFlow Qwen + .env 配置示例）写成 Quick Start，删掉会失败的 `gpt-4o` 写法

3. **检查 GitHub Actions 实际运行历史**：`gh run list --limit 10`

### 短期验证（1-2 天）

4. **扩展 golden cases 为两类**：
   - FakeModel 确定性 case（≥6 个，覆盖 happy path + edge case）——无需 API key，进 CI
   - 真实 API key case（保留现有 4 个）——schedule/manual trigger

5. **本地 `docker compose build && up` 验证一次**：构建失败的话，修复 Dockerfile

6. **修 CI 逃生舱**：`mypy src/ || true` → 去掉 `|| true`（或配置 `--ignore-missing-imports` 后去掉）

### 后续建设（本周内评估）

7. Validator 对外叙事降级：代码不变，把 AGENTS.md/docs 里的"Grounding by Construction"改为"Structured Traceability"
8. Web API 与 CLI 的定位对齐：确认 Dockerfile CMD 跑的是正确的产品形态
9. 真实模型 Pass 率基线：用 ≥10 个 golden case 跑真实模型，记录准确率

---

## 7. 我不知道

- **真实模型在 golden cases 上的 Pass 率**——如果 < 75%，整个"benchmark 化"叙事推迟。这是最该先回答的问题。
- **291 个测试中断言强度分布**——如果大量是 `assert report.status == "ok"` 弱断言，291 这个数字的有效信息量远低于表面。
- **`sentiment/`、`compliance/`、`observability/` 是否已接入主流程**——如果是独立竖井，项目复杂度被高估，应收敛。
- **ClaimsLedger 在真实多轮 Agent 推理下是否出现"claim 间互相矛盾"**——mock 测试不会暴露，只有真实运行才知道。

---

## 附录：Council 元数据

- **顾问完成度**: 5/5 完整返回
- **判断一致性**: 4 个收敛点获 ≥4 顾问一致支持
- **删除弱观点**: 4 条
- **改变判断路径的观点**: 5 条
- **最大不确定性**: 真实模型 Pass 率 + 测试断言强度分布
