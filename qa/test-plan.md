# Test Plan — petfish_BI_Cli

## Current State (verified 2026-07-08)

- **299 tests collected**, 291 passed, 4 skipped (web API, need fastapi), 4 deselected (integration, need API key)
- **ruff**: All checks passed
- **mypy**: continue-on-error (Alpha framework stubs missing)
- **CI**: GitHub Actions workflow exists, no remote configured (local only)

## Test Pyramid

### Component Unit Tests (287 tests, FakeModel/mock-based)

| Module | Tests | What's Tested |
|---|---|---|
| Domain | 6 | BIQuery/BIReport frozen dataclass, defaults, findings structure |
| Grounding | 17 | Claim/ClaimsLedger/ClaimsRegistry + OutputValidator substring+number matching |
| Enhanced Validator | 20 | Chinese number parsing, T1-T5 truth labels, fuzzy matching |
| Semantic Layer | 12 | 5 YAML files parse, entity aliases, JSON path extraction |
| Tools | 23 | ExploreDataSourcesTool + LoadDataTool (real data) + analyze_claims |
| Sentiment | 10 | Lexicon (pos/neg/negation/neutral) + SentimentAnalysisTool |
| Agent | 5 | BIAgentStrategy inherits ReAct, system prompt has traceability rules |
| BIApplication | 6 | Architecture spike (FakeModel), session tracking, parse error, BudgetExceeded |
| Ingestion | 9 | CROCS CSV + JD JSON + TMALL JSONL + ROSE JSONL real data |
| Config | 25 | Settings YAML loading, env overrides, model factory, prompt manager |
| Observability | 18 | MetricsCollector, alerting rules, SLA tracking, audit logger |
| Compliance | 13 | PII redaction, data locality, SLA config loading |
| Retry | 11 | with_retry decorator, backoff, exception filtering |
| Jobs | 6 | JobRegistry create/get/update/concurrent |
| Persistence | 6 | SessionStore save/load/list/delete/cleanup |
| Embedding/Few-shot | 11 | EmbeddingSelector jieba similarity, FewShotSelector intent-first |
| Temporal | 8 | TimeSlice grouping, period comparison, trend analysis |
| ACID | 4 | JobRegistry thread safety, SessionStore atomic write, Validator consistency |
| Smoke | 3 | All public modules importable |
| CLI | 2 | typer ask/sources commands |
| Golden (definition) | 4 | Case definitions have required fields, diverse intents |
| Conftest | 1 | Env isolation fixture works |

### Integration Tests (4 tests, require real API key)

| Case | Query | Expected | Status |
|---|---|---|---|
| jd_avg_price_lookup | CROCS在京东的均价 | ok, "424" in answer | ⚠️ Real model returned 561.01 (data changed) |
| tmall_vs_jd_comparison | 京东和天猫价格差异 | ok | ⚠️ validation_failed (real model) |
| tmall_shop_count | 天猫CROCS店铺数 | ok | ⚠️ KeyError (model passed wrong args) |
| insufficient_data_handling | 拼多多销量 | no_data | ⚠️ Not run |

**Known gap**: Integration tests are marked `@pytest.mark.integration` and deselected in CI. They only run manually with `pytest -m integration`. Golden case expected values need updating after real model runs.

## Honest Limitations

1. **291 component tests measure scaffolding correctness, not BI correctness** — all use FakeModel
2. **Integration tests have 0% pass rate on real data** — expected values are stale, model behavior is non-deterministic
3. **No end-to-end test in CI** — the query→tools→claims→report→validation chain is only tested with mocks
4. **Validator is regex-based** — catches fabricated numbers but not semantic misinterpretation
5. **4 skipped tests** — Web API tests need fastapi installed; should be in `web` extra

## Recommended Next Steps

1. **Update golden case expected values** based on real model runs (outputs/sample-*.json has actual answers)
2. **Split golden cases**: FakeModel-deterministic (no API key, CI) + real API (manual trigger)
3. **Add Web API tests to CI** by installing `--extra web` in CI
4. **Define "correct BI answer" rubric** — what counts as a correct answer? Needs human verification against references/
