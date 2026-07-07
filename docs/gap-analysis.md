# Production Readiness Gap Analysis

> **基于**: Council Evaluation (2026-07-07)
> **方法**: 从 5 顾问判断中提取收敛 gap + 分级 + 估时

---

## Gap 总览

| 级别 | 数量 | 含义 |
|---|---|---|
| 🔴 **BLOCKER** | 5 | 不修不能上线 |
| 🟡 **HIGH** | 6 | 不修上线后有故障风险 |
| 🟢 **MEDIUM** | 5 | 影响体验/可信度但不阻塞 |
| ⚪ **LOW** | 4 | 长期改进项 |

---

## 🔴 BLOCKER（5 项）

### B1: Web API 无认证/限流/CORS

**来源**: Outsider #4, Executor #1
**现状**: `web.py` 是裸 FastAPI，`POST /analyze` 公开可触发 LLM 调用（成本+滥用双风险）
**修复**:
- 加 API key 中间件（读 `BI_CLI_API_KEY` env）
- CORS 默认 deny
- rate limit: 每 key 10 req/min
**估时**: 2h
**验证**: 未授权请求返回 401；授权请求正常

### B2: JobRegistry 无 TTL/上限 → OOM

**来源**: Executor #2
**现状**: `jobs.py` `_registry._jobs` 内存 dict 无限增长；`asyncio.create_task` 进程重启后 job 永远 pending
**修复**:
- `create()` 时 `len > 1000` 拒绝或淘汰最旧
- 后台清理 `>30min` 的 pending/running
- job 状态加 `expired` 标签
**估时**: 2h
**验证**: 创建 1001 个 job 后拒绝；30min 后旧 job 标记 expired

### B3: 真实模型准确率零基准

**来源**: Critic #2, Outsider #8, Executor #4
**现状**: 169 测试全是 FakeModel（测机制不测质量）；4 个集成测试只验证连通性不验证准确率
**修复**:
- 建 10-20 个 golden cases（query + 已知正确答案）
- 真实模型跑 golden cases，记录准确率/延迟/成本
- 阈值: 准确率 ≥ 80%，P95 延迟 < 30s，单次成本 < $0.10
**估时**: 1 人天
**验证**: golden case suite 通过率 ≥ 80%

### B4: petfishframework 版本未锁

**来源**: Critic #3, Executor #3
**现状**: `pyproject.toml` 写 `petfishframework>=0.1.4`，Alpha 框架 minor bump 可能 break
**修复**:
- `>=0.1.4` → `==0.1.4`
- 加 `framework.py` contract 测试（`Agent.run_structured` / `Task` / `Budget` 接口断言）
**估时**: 1h
**验证**: 故意装 0.1.5（如果存在），contract 测试报警

### B5: outputs/ 和 examples/ 空——无可验证产出

**来源**: Opportunity #1, Outsider #1
**现状**: BI 工具的全部价值在报告产出，仓库里**没有一份样本报告**
**修复**:
- 4 个数据源各生成 1 个 golden example JSON 报告
- 放入 `outputs/examples/` + `examples/`
- README 加"90秒看懂产品"section 引用这些报告
**估时**: 4h
**验证**: 仓库有 ≥4 份可读的样本报告

---

## 🟡 HIGH（6 项）

### H1: README 与实际验证路径矛盾

**来源**: Outsider #3
**现状**: QuickStart 写 `OPENAI_API_KEY="sk-..."` + `gpt-4o`，但验证用 SiliconFlow Qwen2.5-72B
**修复**: 对齐 README，加 SiliconFlow 配置示例
**估时**: 1h

### H2: Agent 无 retry/backoff

**来源**: Executor #5
**现状**: LLM 调用失败（网络/超时/parse_error）直接返回 failed，无重试
**修复**: 加 `tenacity` 指数退避 2 次重试
**估时**: 2h

### H3: Session 无持久化

**来源**: Executor #8
**现状**: `application.py` `self._sessions` 内存 dict，重启丢失
**修复**: event store 落 SQLite（petfishframework 是 event-sourced，应该有 hook）
**估时**: 1 人天

### H4: Grounding validator regex 粗糙

**来源**: Critic #1, Opportunity #2
**现状**: `validator.py` 用 `\d+\.?\d*` 抓数字。LLM 写"约424"/"四百二十四"会漏检
**修复**:
- 加中文数字解析（一二三.../万/亿）
- 加"约/大约/近"等模糊修饰词检测
- 输出 confidence score 而非 binary pass/fail
**估时**: 4h

### H5: 单次快照数据——无趋势/增量能力

**来源**: Outsider #2
**现状**: 4 个数据源全集中在 2026-06-05，无时间维度变化
**修复**: 补充 ≥2 个时间点的数据快照（或声明"当前为 PoC 数据"）
**估时**: 数据采集依赖外部，代码层 2h

### H6: 无 Prompt 回归基线

**来源**: Executor #6
**现状**: 改 system_prompt/few_shot 无安全网
**修复**: system_prompt + few_shot 哈希记到 `qa/prompt_baseline.txt`，CI 断言一致
**估时**: 1h

---

## 🟢 MEDIUM（5 项）

### M1: 成本/延迟无基准

**来源**: Opportunity/Outsider/Executor 一致
**修复**: 在 golden case suite 中记录 token 消耗/延迟/cost
**估时**: 含在 B3 中

### M2: 无结构化日志/可观测性

**修复**: 加 JSON line 日志 + `/health` 返回 job 数/最近错误率
**估时**: 4h

### M3: 数据合规未声明

**来源**: Outsider #6
**修复**: 加 `DATA_SOURCES.md` 声明数据来源/授权/使用边界
**估时**: 1h

### M4: 无 Dockerfile/docker-compose

**修复**: M4-T042 已规划
**估时**: 4h

### M5: 无 CI pipeline

**修复**: M4-T043 已规划（pytest + ruff + mypy）
**估时**: 2h

---

## ⚪ LOW（4 项）

### L1: Few-shot 未做 embedding-based 相似度选择
### L2: ROSE HTML 报告未解析
### L3: Web API 无 OpenAPI 文档增强
### L4: 无多租户隔离

---

## 实施路线图

### Phase 1: 止血（1 人天）

```
B1 (Web auth) + B2 (Job TTL) + B4 (版本锁) + H1 (README 对齐)
```

### Phase 2: 验证（1-2 人天）

```
B3 (golden cases) + B5 (sample outputs) + H2 (retry) + H6 (prompt baseline)
```

### Phase 3: 加固（5-8 人天）

```
H3 (Session 持久化) + H4 (validator 增强) + M2 (可观测性) + M4 (Docker) + M5 (CI)
```

### Phase 4: 增值（可选）

```
H5 (多时间点数据) + M3 (合规声明) + L1-L4
```

---

## 验收标准

"Production Ready" 的最低验收线（Phase 1+2 完成）:

- [ ] Web API 有 API key 认证 + rate limit
- [ ] JobRegistry 有 TTL + 上限
- [ ] petfishframework 版本锁定 `==0.1.4`
- [ ] ≥10 个 golden cases 准确率 ≥ 80%
- [ ] ≥4 份样本报告在 `outputs/examples/`
- [ ] README QuickStart 与实际验证路径一致
- [ ] Agent 失败有 retry
- [ ] Prompt 改动有回归基线

达成以上 8 项 = **内部 production ready**。
达成 Phase 3 = **私有 Web production ready**。
达成 Phase 4 = **对外 SaaS ready（需额外合规审查）**。
