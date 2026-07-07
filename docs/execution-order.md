# Execution Order — Cross-Plan Sequencing

## Three Plans

| Plan | Doc | Milestone | Focus |
|---|---|---|---|
| 模型接入 | `plan-model-integration.md` | M4 | 解除 FakeModel 阻塞 |
| 分析深度 | `plan-analysis-depth.md` | M5 | Sentiment + Trend + Cross-source |
| 配置化 | `plan-config-system.md` | M6 | RAG + MCP + Prompt 统一配置 |

## Dependency Graph

```
M4 (Model) ──────► M5 (Analysis)
    │                   │
    │  model.roles      │  sentiment LLM batch
    │  复用              │  复用 model.roles.primary
    ▼                   ▼
M6 (Config) ◄─── 独立，可与 M4/M5 并行
```

- M5 依赖 M4：sentiment LLM batch 需要 `model.roles.primary` 真实模型
- M6 独立于 M4/M5：config system 可并行开发，但集成测试需要 M4 完成

## Recommended Sequence

```
Week 1: M4 (T001-T006)     ← 阻塞解除，真实查询可运行
Week 2: M5 (T001-T008)     ← 分析深度，BI 价值体现
Week 3: M6 (T001-T011)     ← 配置化，扩展性
```

M4 和 M6 前 3 个任务（MCP/RAG/Prompt loader 骨架）可并行。

## Per-Plan Task Summary

### M4: Real Model Integration (6 tasks)

| Task | Test | Implementation |
|---|---|---|
| T001 | `test_settings_loads_yaml` | `config/settings.py` |
| T002 | `test_env_overrides_yaml` | env 变量映射 |
| T003 | `test_model_factory_openai` | `config/model_factory.py` |
| T004 | `test_model_factory_fallback` | fallback 降级 |
| T005 | `test_make_bi_agent_uses_settings` | `framework.py` 改造 |
| T006 | `test_smoke_real_model` @integration | smoke test suite |

### M5: Analysis Depth (8 tasks)

| Task | Test | Implementation |
|---|---|---|
| T001 | `test_lexicon_sentiment_磨脚` | `sentiment/lexicon.py` |
| T002 | `test_lexicon_sentiment_舒服` | 同上 |
| T003 | `test_llm_sentiment_batch` | `sentiment/llm_batch.py` |
| T004 | `test_sentiment_tool_returns_claims` | `agent/tools/sentiment.py` |
| T005 | `test_sentiment_grounding` | ClaimsRegistry 集成 |
| T006 | `test_trend_tool_daily_buckets` | `agent/tools/trend.py` |
| T007 | `test_cross_source_compare` | `agent/tools/cross_source.py` |
| T008 | `test_smoke_sentiment_on_real_data` @integration | 集成测试 |

### M6: Configurable RAG/MCP/Prompts (11 tasks)

| Task | Test | Implementation |
|---|---|---|
| T001 | `test_mcp_loader_empty_config` | `config/mcp_loader.py` |
| T002 | `test_mcp_loader_resolves_env_vars` | `_resolve_env()` |
| T003 | `test_mcp_loader_connects_stdio` @integration | `connect_stdio` 集成 |
| T004 | `test_chinese_retriever_tokenizes_cjk` | `retrieval/chinese_retriever.py` |
| T005 | `test_crag_retriever_routes_relevant` | CRAG 集成 |
| T006 | `test_rag_loader_builds_from_config` | `config/rag_loader.py` |
| T007 | `test_prompt_manager_loads_system_prompt` | `config/prompt_manager.py` |
| T008 | `test_prompt_manager_hot_reload` | mtime cache |
| T009 | `test_few_shot_intent_first` | `_select()` |
| T010 | `test_promptfoo_regression` | promptfoo eval |
| T011 | `test_make_bi_agent_full_config` | `framework.py` 全集成 |

## Total: 25 tasks across 3 milestones

## Config File Evolution

```
M4: configs/bi_cli.yml (model + budget 段)
M5: configs/bi_cli.yml (+ analysis 段)
M6: configs/bi_cli.yml (+ mcp + retrieval + prompts 段)
```

最终 `configs/bi_cli.yml` 包含全部 5 段，用户通过编辑一个文件控制整个系统。

## New Dependencies

| Plan | Dependency | Install Command |
|---|---|---|
| M4 | 无新增（petfishframework[openai] 已是 optional dep） | `uv sync --extra openai` |
| M5 | 无新增（jieba + snownlp 已安装） | — |
| M6 | sentence-transformers (BGE-zh embedding) | `uv sync --extra rag` |

## New ADRs

| Plan | ADR | Decision |
|---|---|---|
| M4 | ADR-016 | 分层配置加载（defaults < YAML < env < CLI） |
| M4 | ADR-017 | 多模型角色（primary/fallback/testing） |
| M5 | ADR-018 | 混合情感分析（lexicon 60% + LLM 40%） |
| M5 | ADR-019 | Sentiment 输出作为 ClaimsLedger entries |
| M6 | ADR-020 | MCP auto-loader（YAML → connect_stdio → Tool） |
| M6 | ADR-021 | ChineseEmbeddingRetriever（解决 MemoryRetriever 中文分词） |
| M6 | ADR-022 | Prompt 版本管理（Git + mtime 热重载） |

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| M4 API key 泄露 | 禁止写入文件；只从 env 读；`.gitignore` 含 `.env` |
| M5 LLM 批处理成本失控 | Budget 限制 + 批量缓存 + lexicon 前置过滤 |
| M6 MCP 子进程泄漏 | `cleanup()` 上下文管理器 + 信号处理 |
| M6 sentence-transformers 下载慢 | 首次使用时下载；CI 缓存模型目录 |
