from __future__ import annotations

import json
from pathlib import Path

import typer

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.cli.config_cmd import config_app
from petfish_bi_cli.domain import BIQuery

app = typer.Typer(help="AI for BI CLI — query e-commerce data via natural language.")
app.add_typer(config_app, name="config")


@app.command()
def ask(
    query: str = typer.Argument(help="BI query in natural language"),
    data_source: list[str] = typer.Option(
        [], "--data-source", "-s", help="Filter to specific data sources"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON report to file"),
    session_id: str | None = typer.Option(None, "--session-id", help="Resume a previous session"),
):
    """Ask a BI question and get a JSON report."""
    bi_app = BIApplication()
    bi_query = BIQuery(
        prompt=query,
        data_sources=tuple(data_source),
    )
    report = bi_app.execute(bi_query)

    output_json = json.dumps(
        {
            "answer": report.answer,
            "data": report.data,
            "session_id": report.session_id,
            "status": report.status,
        },
        ensure_ascii=False,
        indent=2,
    )

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(output_json, encoding="utf-8")
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(output_json)


@app.command()
def sources():
    """List available data sources."""
    from petfish_bi_cli.config.settings import load_settings
    from petfish_bi_cli.config.source_registry import SourceRegistry

    settings = load_settings()
    registry = SourceRegistry(
        config=settings.raw,
        data_root=Path(settings.data.root),
        semantic_dir=Path(settings.data.semantic_dir),
    )
    for decl in registry.all_sources().values():
        typer.echo(f"  {decl.source_id} ({decl.type}): {decl.description}")


@app.command()
def health():
    """Check if the system is properly configured."""
    from petfish_bi_cli.config.settings import load_settings

    try:
        settings = load_settings()
        data_root = Path(settings.data.root)
        model_ok = settings.model.provider in ("fake", "openai", "anthropic")
        data_ok = data_root.exists()
        status = "ok" if (model_ok and data_ok) else "degraded"
        typer.echo(
            json.dumps(
                {
                    "status": status,
                    "model_provider": settings.model.provider,
                    "model_name": settings.model.name,
                    "data_root": str(data_root),
                    "data_root_exists": data_ok,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if status != "ok":
            raise typer.Exit(1) from None
    except Exception as exc:
        typer.echo(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        raise typer.Exit(1) from exc


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    hot_reload_policy: bool = typer.Option(
        True, "--hot-reload-policy/--no-hot-reload-policy",
        help="Watch configs/policy.yml for changes",
    ),
):
    """Start the web API server."""
    if hot_reload_policy and Path("configs/policy.yml").exists():
        from petfishframework.policies.hot_reload import PolicyHotReloader

        reloader = PolicyHotReloader("configs/policy.yml")
        reloader.start()
        typer.echo("Policy hot-reloader started (watching configs/policy.yml)")

    try:
        import uvicorn

        uvicorn.run("petfish_bi_cli.web:app", host=host, port=port)
    except ImportError:
        typer.echo("uvicorn not installed. Run: uv sync --extra web")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
