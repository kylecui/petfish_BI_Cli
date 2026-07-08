# Code Review Checklist — petfish_BI_Cli

> Last verified: 2026-07-08 (commit 48b87ee)

## Build & Test

- [x] `uv run pytest tests/ -m "not integration"` — 291 passed, 4 skipped, 4 deselected
- [x] `uv run ruff check src/ tests/` — All checks passed
- [~] `uv run mypy src/` — continue-on-error (Alpha framework stubs missing; not blocking)

## Architecture (ADR-004~015)

- [x] ADR-004: BIApplication transport-agnostic
- [x] ADR-005: Tools hold `data_root: Path` directly
- [x] ADR-006: Agent frozen=True; Session UUID per-request
- [x] ADR-007: CLI sync; Web async + JobRegistry
- [x] ADR-008: `petfishframework==0.1.4` pinned
- [x] ADR-009: Domain models use bare `dict`
- [x] ADR-010: 4 independent ingestion adapters
- [x] ADR-011: Query understanding via ReAct Tools
- [x] ADR-012: Structured Traceability (renamed from "Grounding by Construction")
- [x] ADR-013: OutputValidator substring + number matching
- [x] ADR-014: YAML semantic layer (5 files)
- [x] ADR-015: BIAgentStrategy subclasses ReAct._system_prompt()

## Traceability Pipeline

- [x] LoadDataTool returns ClaimsLedger (not raw data)
- [x] ClaimsRegistry collects claims via DI
- [x] OutputValidator rejects unverified numbers
- [x] BIApplication.execute() runs validator after run_structured()
- [~] Validator catches fabricated numbers (regex-based, not semantic)
- [~] ClaimsLedger guarantees provenance, NOT truthfulness (model can still misinterpret)

## Transport Isolation

- [x] `application.py` has zero transport imports
- [x] CLI and Web are thin adapters
- [x] No print()/sys.exit() in Tools or Application

## Error Handling

- [x] BudgetExceeded → status="budget_exceeded"
- [x] Parse error → status="parse_error"
- [x] Validation failure → status="validation_failed"
- [~] load.py: missing 'source' parameter now returns error (not crash)

## Sample Outputs

- [x] outputs/sample-jd_avg_price.json — status=ok, answer="CROCS在京东的均价是561.01元"
- [x] outputs/sample-tmall_avg_price.json — status=ok, answer="421.16元"
- [~] outputs/sample-jd_vs_tmall.json — status=parse_error (model tool call issue)
- [~] outputs/sample-crocs_sentiment.json — status=parse_error (same root cause)

## Honest Gaps (from Council Review 2026-07-08)

- [ ] Integration tests have 0% pass rate on real data (expected values stale)
- [ ] Dockerfile not verified to build
- [ ] CI has no remote configured
- [ ] No end-to-end test in CI
- [ ] Validator doesn't support Chinese numbers (两千三百/2.3万)
- [ ] `outputs/` has 4 samples but 2 are parse_error
- [ ] Golden case expected values need updating after real model runs
- [ ] ClaimsLedger provenance ≠ truthfulness (semantic correctness unverified)
