#!/usr/bin/env bash
set -euo pipefail

echo "=== petfish BI CLI Setup ==="

python3 --version 2>/dev/null || { echo "ERROR: Python 3.10+ required"; exit 1; }

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Installing dependencies..."
uv sync --extra web --extra openai

if [ ! -f configs/bi_cli.yml ]; then
    if [ -f configs/bi_cli.example.yml ]; then
        cp configs/bi_cli.example.yml configs/bi_cli.yml
        echo "Created configs/bi_cli.yml from template"
    else
        echo "WARNING: No configs/bi_cli.yml found. Run 'petfish-bi config init' or create manually."
    fi
fi

echo "Verifying setup..."
uv run petfish-bi health || { echo "ERROR: Health check failed"; exit 1; }

echo ""
echo "=== Setup complete ==="
echo "Quick start:"
echo "  petfish-bi ask \"CROCS在京东的均价是多少？\""
echo "  petfish-bi sources"
echo "  petfish-bi web --port 8000"
