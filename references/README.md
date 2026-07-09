# references/

This directory holds data source files for the BI CLI.

## Structure

```
references/
├── mock_*.json/csv/html    # Mock data (tracked in git, safe for public repo)
├── semantic/*.yml          # Data source metadata (tracked, schema descriptions only)
├── JD_*.json               # Real data (gitignored, local only)
├── TMALL_*.json            # Real data (gitignored, local only)
├── CROCS_*.csv             # Real data (gitignored, local only)
└── ROSE_*.json/html        # Real data (gitignored, local only)
```

## Mock Data

Mock files (`mock_*`) contain **fake data** with the same structure as real data:
- Fake product names, prices, shop names
- Fake user names and comment text
- Example URLs (example.com)

They allow the project to run and demonstrate functionality without real e-commerce data.

## Adding Real Data

Place real data files alongside mock files. The system automatically prefers real data when available:

```bash
# Copy your data (any name, declare in bi_cli.yml sources:)
cp my_jd_data.json references/my_jd_data.json

# The tools will use real data automatically
petfish-bi ask "均价是多少？"
```

Real data patterns are gitignored — they will never be committed.
