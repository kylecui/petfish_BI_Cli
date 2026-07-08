FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra openai --extra web || \
    uv sync --no-dev --extra openai --extra web

COPY src/ src/
COPY references/ references/
COPY configs/ configs/

RUN uv pip install -e .

ENTRYPOINT ["uv", "run", "petfish-bi"]
CMD ["--help"]
