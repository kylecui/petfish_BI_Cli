<!-- BEGIN pack: opencode-skill-pack-testcases-usage-docs -->
# Test Cases & Usage Docs Skill Pack Rules

This pack provides two complementary skills: generating test cases from real project code, and generating usage documentation from real project capabilities.

## Skill Routing (强制)

### Rules

1. When the user asks to generate **test cases, test strategy, test matrix, or test plan** from a project, **MUST** route to `generate-test-cases`. Do NOT route to `generate-usage-docs`.
2. When the user asks to generate **README, Quick Start, API docs, CLI docs, FAQ, or troubleshooting guides** from a project, **MUST** route to `generate-usage-docs`. Do NOT route to `generate-test-cases`.
3. Both skills require a **project inventory step first**: run `uv run scripts/project_inventory.py .` before generating artifacts. Do not skip this step.
4. When the user asks for both tests and docs in the same request, run `generate-test-cases` and `generate-usage-docs` sequentially (inventory once, then both generation steps). Do not merge them into a single pass.
5. Both skills operate on **real project code and design docs** — do not generate generic/template artifacts without first reading the actual project.

### Conflict Resolution

- "Write tests for this project" = `generate-test-cases`.
- "Document this project" = `generate-usage-docs`.
- "Help me ship this project" (ambiguous) → ask whether the priority is test coverage or user-facing documentation, then route accordingly.
- If the user provides a design doc or spec as input, both skills can use it — but route based on the desired output type (tests vs docs).

## generate-test-cases Workflow

1. Run project inventory: `uv run scripts/project_inventory.py .`
2. Build traceability map: capabilities → test targets
3. Generate layered test artifacts:
   - Test strategy (scope, risk areas, coverage goals)
   - Test matrix (feature × scenario × priority)
   - Test cases (input, expected output, pass/fail criteria)
4. Output to `tests/` or designated output directory

## generate-usage-docs Workflow

1. Run project inventory: `uv run scripts/project_inventory.py .`
2. Identify target audience (end user / developer / operator)
3. Identify project capabilities (CLI, API, config, integrations)
4. Build doc set:
   - README (overview, install, quick start)
   - API / CLI reference
   - FAQ and troubleshooting
5. Output to `docs/` or designated output directory

## Behavioral Rules

- Always run project inventory before generating any artifact. Do not generate from assumptions.
- Test cases must be traceable to specific project capabilities identified in the inventory.
- Usage docs must reflect actual project behavior, not generic boilerplate.
- If the project inventory reveals missing or ambiguous capabilities, flag them before generating — do not silently fill gaps with invented behavior.
- Generated test cases must include: input, expected output, and pass/fail criteria. Vague test descriptions are not acceptable.
- Generated docs must include: at least one working example per capability documented.

## Output Format

**generate-test-cases** outputs:
1. Test strategy document — scope, risk areas, coverage goals
2. Test matrix — feature × scenario × priority table
3. Test case files — structured cases with input/output/criteria

**generate-usage-docs** outputs:
1. README — overview, install, quick start
2. Reference docs — API / CLI / config
3. FAQ / Troubleshooting — common issues and resolutions
<!-- END pack: opencode-skill-pack-testcases-usage-docs -->

<!-- BEGIN pack: trustskills-governance-pack -->
# Trust Skills Governance Pack Rules

This pack provides skill trust scanning, governance level assignment, and manifest generation/verification for PEtFiSh skill packs.

## Skill Routing (强制)

### Rules

1. When the user asks to **scan skills for trust, safety, or governance issues**, **MUST** route to `skill-trust-governance`.
2. When the user asks to **generate or verify a trust manifest** for a skill or pack, **MUST** route to `skill-trust-governance`.
3. When the user asks to **assign or review governance levels** (allow / allow_with_ask / sandbox_required / manual_review_required / deny) for skills, **MUST** route to `skill-trust-governance`.
4. When the user asks to **redline** a skill (flag it as requiring manual review or denial), **MUST** route to `skill-trust-governance`.
5. The entrypoint for all trust operations is: `uv run .opencode/skills/skill-trust-governance/scripts/trust_scan.py`. Do not invoke `trustskills` CLI directly without going through this entrypoint.

### Conflict Resolution

- Trust governance vs security audit: `skill-trust-governance` handles **governance classification and manifest management** (what level of trust to grant a skill). `skill-security-auditor` handles **vulnerability and risk scanning** (what security risks a skill poses). They are complementary — run security audit first, then use findings to inform governance level assignment.
- When the user asks to "check if a skill is safe to install", route to `skill-security-auditor` for risk findings, then `skill-trust-governance` for governance decision.
- When the user asks to "publish a skill", the governance manifest must be generated by `skill-trust-governance` before the `quality-gate` publish flow.

## Governance Levels

| Level | Meaning | Agent Behavior |
|---|---|---|
| `allow` | Trusted, no restrictions | Execute without prompting |
| `allow_with_ask` | Trusted but requires confirmation for sensitive actions | Prompt user before sensitive operations |
| `sandbox_required` | Must run in isolated environment | Do not execute outside sandbox |
| `manual_review_required` | Flagged for human review before use | Block execution, notify user |
| `deny` | Rejected, must not be used | Refuse to load or execute |

## trust_scan.py Modes

- **scan**: Analyze a skill directory and produce a trust report
- **manifest**: Generate a signed trust manifest for a skill
- **verify**: Verify an existing trust manifest against current skill content
- **redline**: Flag a skill at `manual_review_required` or `deny` level

## Behavioral Rules

- Never assign `allow` governance level without completing a full scan. Partial scans must result in `manual_review_required` at minimum.
- Trust manifests must be regenerated whenever skill content changes. Stale manifests are treated as `manual_review_required`.
- `deny`-level skills must not be loaded, executed, or referenced in routing rules.
- When a scan finds issues, report them with the specific governance level recommendation and the reason. Do not silently downgrade to `allow`.
- Governance decisions must be logged with: skill path, scan timestamp, findings summary, assigned level, and agent ID.

## Output Format

**scan** output:
1. Trust report — findings per skill file, risk signals detected
2. Recommended governance level with justification

**manifest** output:
1. Signed trust manifest file (saved alongside skill)
2. Manifest summary — skill path, level, timestamp, hash

**verify** output:
1. Verification result: PASS / FAIL / STALE
2. If FAIL or STALE: diff of what changed and recommended action

**redline** output:
1. Updated governance level in manifest
2. Redline reason and required remediation steps before level can be upgraded
<!-- END pack: trustskills-governance-pack -->

---

# Project Agent Guide — petfish_BI_Cli

## Project Goal

petfish_BI_Cli 是一个 **AI for BI** 的 CLI 应用：客户通过 CLI 发出咨询请求，系统从电商原始数据（CSV/JSON，格式未必统一）中获取信息，按需协助分析，最终返回 JSON（必须）+ 富文本内容（加分）。基于 [petfishframework](https://pypi.org/project/petfishframework/) 构建 AI Agent 编排层。

未来扩展方向：BI 分析深化、舆情分析（品牌/代言人）、反馈分析、框架本身研究。

## Project Type

`code` — Python CLI 工具（src 布局）+ AI Agent 编排。

## Tech Stack

- **语言**: Python ≥ 3.10（实测环境 3.12.3）
- **AI 框架**: `petfishframework` (v0.1.4 Alpha) — Agent recipe (model + reasoning + tools + retriever)、event-sourced Session、MCP-first Tool contracts、Pass^k 可靠性度量
- **包管理**: uv 0.11.17
- **测试**: pytest
- **Lint**: ruff (E/F/I/B, line-length=100, target py310)
- **类型**: mypy (py310, warn_unused_configs)
- **可选模型适配**: openai>=1.0 / anthropic>=0.40 / mcp>=1.0

## Working Principles

- 先理解 BI 咨询意图，再检索数据，再分析，最后产出 JSON。
- 原始数据格式不统一时，先建 ingestion adapter，不要假设 schema。
- JSON 输出是 must-have，富文本是 nice-to-have；两者解耦。
- Agent 的可靠性来自架构（petfishframework 的 Session 审计 + Budget），不要绕过。
- 不要把模型常识当作真实电商数据；所有 claim 必须可追溯到 raw data。
- 网络操作失败（API、包安装）至少重试两次再换方案。
- 不修改其它仓库；上游问题通过 issue 反馈。

## Directory Map

```text
petfish_BI_Cli/
├── src/                    # 源码（待填充：petfish_bi_cli 包）
│   └── petfish_bi_cli/
│       ├── main.py         # CLI entrypoint (typer/click)
│       ├── agent/          # Agent 定义（ReAct + tools）
│       │   └── tools/      # 自定义 Tool：CSV/JSON ingestion、report gen
│       ├── models/         # Pydantic 数据模型
│       └── config/         # settings.py
├── tests/                  # pytest（FakeModel 无需 API key）
├── references/             # 原始数据样本（CROCS/JD/TMALL/ROSE）
├── outputs/                # 生成的 JSON/富文本报告
├── docs/                   # architecture.md / api.md / development.md
├── qa/                     # code-review-checklist.md / test-plan.md
├── scripts/                # 工具脚本（含 project_inventory.py 等）
├── configs/                # 运行时配置
├── examples/               # 用法示例
├── mcp/                    # MCP 配置模板（占位符）
├── .opencode/              # OpenCode 配置 + 已装 9 个 skill pack
└── .petfish/fish-trail/    # 话题治理状态
```

## Preferred Tools

- **uv** — Python 项目与依赖管理
- **pytest** — 测试（配合 petfishframework 的 `FakeModel` 做无 API key 测试）
- **ruff** — lint（E/F/I/B）
- **mypy** — 类型检查
- **petfishframework** — AI Agent 编排（Agent / Session / Tool / ReAct）
- **typer 或 click** — CLI 入口（框架不提供，需自建）
- **pandas**（按需）— CSV/JSON 数据处理
- **pydantic** — JSON 输出 schema 与校验

## Skills（已安装 9 个 pack）

| Pack | 用途 |
|---|---|
| petfish-toolchain-skill | skill 作者/lint/audit/gate 全工具链 |
| repo-deploy-ops-skill-pack | 部署/运维/回滚 |
| opencode-skill-pack-testcases-usage-docs | 测试用例 + 使用文档生成 |
| petfish-style-skill | 写作风格（去 AI 味、风格提取） |
| judgment-calibration-pack | 反迎合校准 + 五人顾问团 |
| fish-trail | 话题治理 + 分层记忆 |
| research-skill-pack | 54 个研究 skill（BI/舆情/反馈研究用） |
| trustskills-governance-pack | skill 信任治理 |
| fish-reflection-pack | 结构化反思 |

`code` profile 推荐的 `deploy`、`testdocs` 已装；`petfish` 基础 pack 未装（可选）。

## MCP

模板在 `mcp/`。现有 `opencode.json` 已配置 `context-state` MCP（fish-trail 用）。新增 MCP 服务时只用占位符，禁止提交真实密钥。

## Quality Gates

- README 说明项目目标与用法。
- `tasks/backlog.md` 或 roadmap 存在。
- QA checklist 存在（`qa/`）。
- 输出与源数据分离（`outputs/` vs `references/`）。
- 有测试或测试计划；Agent 行为用 `FakeModel` 做确定性测试。
- JSON 输出必须通过 pydantic schema 校验。
- 所有数据 claim 必须可追溯到 `references/` 中的原始记录。

## Do Not

- 不写密钥/API key/token 到任何文件。
- 不隐藏 shell 命令。
- 不静默覆盖用户文件。
- 不把临时输出混入正式材料。
- 不把模型常识当作真实电商数据。
- 不绕过 petfishframework 的 Session/Budget 审计机制。
- 不假设 raw data schema 统一；必须先建 ingestion adapter。

## Development Gotchas

<!--
记录代码库中非代码自解释的约定、已知陷阱、关键设计约束。
规则：
- 每条必须是"违反会导致 bug，且代码本身无法自解释"的约束
- 上限 10 条；超过时审视哪些已通过代码改进不再需要
- 一次性排查过程不记录
-->

- 待项目代码成型后补充。当前已知：petfishframework 处于 Alpha (v0.1.4)，API 可能变动，升级前先看 CHANGELOG。
- raw data 格式不统一（CROCS CSV vs JD/TMALL JSON dump vs ROSE HTML 报告），每个数据源必须独立 ingestion adapter，不要写一个"通用 parser"。
- petfishframework 的 `Agent` 是不可变 recipe；改配置要新建 Agent 实例，不要原地修改。

## Architecture Decisions

<!--
重大技术选型和设计决策的简要记录。
格式：一句话结论 + 指向 docs/ 下完整 ADR 的链接（如有）。
-->

- **ADR-001**: 选用 petfishframework 作为 Agent 编排层（可靠性作为架构属性，event-sourced Session 可审计）。
- **ADR-002**: CLI 入口用 typer/click 自建（框架不提供 CLI boilerplate）。
- **ADR-003**: JSON 输出用 pydantic schema 强约束（must-have），富文本作为独立可选输出。

## Crystallization Triggers

经验沉淀不在每次 commit 后触发。以下时机评估是否有新 gotcha 需记录：

- 完成 ingestion adapter 并处理过格式异常后
- Agent 出现"看起来不是 bug 但其实是"的行为后
- 新增数据源 / 新增 Tool / 新增 reasoning 策略后
- petfishframework 升级后
