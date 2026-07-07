# Code Review Checklist — petfish_BI_Cli

## Build & Test

- [x] `uv run pytest tests/` — 91 passed, 0 failed
- [x] `uv run ruff check src/ tests/` — All checks passed
- [x] `uv run mypy src/ --ignore-missing-imports` — Success: no issues in 23 files

## Architecture (ADR-004~015)

- [x] ADR-004: BIApplication is transport-agnostic (no `import typer`/`import fastapi` in application.py)
- [x] ADR-005: Tools hold `data_root: Path` directly (no premature DataPort)
- [x] ADR-006: Agent shared singleton (frozen=True verified); Session per-request (UUID)
- [x] ADR-007: CLI sync (`execute()`); Web async + JobRegistry (`POST /analyze` → 202 + job_id)
- [x] ADR-008: `petfishframework>=0.1.4` pinned; framework calls in `framework.py` + `strategy.py`
- [x] ADR-009: Domain models use bare `dict` (not `dict[str, Any]`); outside-in TDD
- [x] ADR-010: 4 independent ingestion adapters (CROCS CSV / JD JSON / TMALL JSONL / ROSE JSONL)
- [x] ADR-011: Query understanding via ReAct Tools (explore → load → analyze)
- [x] ADR-012: ClaimsLedger — LLM sees metadata not raw data; ClaimsRegistry DI
- [x] ADR-013: OutputValidator — substring + number matching against claims
- [x] ADR-014: YAML semantic layer (5 files in `references/semantic/`)
- [x] ADR-015: BIAgentStrategy subclasses `ReAct._system_prompt()`

## Grounding Pipeline

- [x] LoadDataTool returns ClaimsLedger (not raw data)
- [x] ClaimsRegistry collects claims via DI (§6.3.1 data flow resolved)
- [x] OutputValidator rejects unverified numbers (T5 hallucination detection)
- [x] BIApplication.execute() runs validator after run_structured()

## Transport Isolation

- [x] `application.py` has zero transport imports (no typer/fastapi)
- [x] CLI (`main.py`) and Web (`web.py`) are thin adapters calling BIApplication
- [x] No `print()`/`sys.exit()` in Tools or Application layer

## Error Handling

- [x] BudgetExceeded → `BIReport(status="budget_exceeded")`
- [x] Parse error → `BIReport(status="parse_error")`
- [x] Validation failure → `BIReport(status="validation_failed")`
- [x] Web errors: HTTP 200 + status field (not 500)

## Data Integrity

- [x] CROCS CSV: skips "无" empty markers, 2034→valid records
- [x] JD JSON: 4 products with real prices
- [x] TMALL JSONL: 23 dumps → 1275 items, price str→float cast
- [x] ROSE JSONL: 58 dumps → 2853 items, brand extraction from title
