# Test Plan — petfish_BI_Cli

## Test Pyramid (91 tests total)

### Domain Unit (6 tests)
BIQuery/BIReport frozen dataclass behavior, defaults, findings structure.

### Grounding (17 tests)
Claim/ClaimsLedger/ClaimsRegistry/ValidationResult + OutputValidator (valid/unverified/mismatch/no-claim/empty/comparison).

### Semantic Layer (12 tests)
5 YAML files parse correctly, entity aliases, JSON path extraction, load_all_metadata.

### Tools (23 tests)
ExploreDataSourcesTool + LoadDataTool (real data) + analyze_claims (avg/sum/min/max/count/compare).

### Agent (5 tests)
BIAgentStrategy inherits ReAct, prompt has grounding rules + data sources + date.

### BIApplication (6 tests)
Architecture spike (T004), session tracking, parse error, no-tool-calls.

### Ingestion (9 tests)
CROCS CSV + JD JSON + TMALL JSONL + ROSE JSONL against real reference files.

### CLI (2 tests) + Jobs (6 tests) + Web API (4 tests)

## Results
- **91 passed, 0 failed** in ~1.1s
- ruff: clean | mypy: 0 issues in 23 files
