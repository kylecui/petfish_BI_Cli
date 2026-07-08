# Deployment Guide — petfish BI CLI

## Quick Start

```bash
git clone <repo-url> petfish-bi
cd petfish-bi
./install.sh
```

## Manual Setup

1. **Install Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Install uv** (Python package manager)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync --extra web --extra openai
   ```

4. **Configure**
   ```bash
   cp configs/bi_cli.example.yml configs/bi_cli.yml
   # Edit configs/bi_cli.yml: set model provider, API key, data sources
   ```

5. **Verify**
   ```bash
   uv run petfish-bi health
   ```

## Configuration

### Model

Edit `configs/bi_cli.yml`:
```yaml
model:
  provider: openai          # openai | anthropic | fake
  name: gpt-4o
  api_key: null             # null = read from OPENAI_API_KEY env var
  temperature: 0.0
```

Set API key:
```bash
export OPENAI_API_KEY="sk-..."
```

### Data Sources

Place data files in `references/` and declare them in config:
```yaml
sources:
  my_products:
    type: json
    path: my_products.json
    description: "Product catalog"
    metrics:
      - name: avg_price
        column: price
        aggregation: avg
```

### BI Scripts

Wrap existing scripts as Agent tools:
```yaml
scripts:
  custom_report:
    command: "python scripts/report.py"
    description: "Custom sales report"
    input_schema:
      type: object
      properties:
        date: { type: string }
```

## Running

### CLI
```bash
petfish-bi ask "CROCS在京东的均价是多少？"
petfish-bi sources
petfish-bi health
```

### Web API
```bash
petfish-bi web --port 8000
# API: POST /analyze  {"query": "..."}
# Health: GET /health
```

### Docker
```bash
docker compose up -d
# Web API available at http://localhost:8000
```

## Data Placement

```
references/
├── jd/                    # JD data
├── tmall/                 # TMALL data
├── crocs/                 # CROCS data
├── semantic/              # Auto-loaded metadata (fallback)
└── your_data/             # Custom data sources
```
