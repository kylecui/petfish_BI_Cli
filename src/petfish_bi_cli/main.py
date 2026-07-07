from __future__ import annotations

import json
from pathlib import Path

import typer

from petfish_bi_cli.application import BIApplication
from petfish_bi_cli.domain import BIQuery

app = typer.Typer(help="AI for BI CLI — query e-commerce data via natural language.")


@app.command()
def ask(
    query: str = typer.Argument(help="BI query in natural language"),
    data_source: list[str] = typer.Option(
        [], "--data-source", "-s", help="Filter to specific data sources"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write JSON report to file"
    ),
    session_id: str | None = typer.Option(
        None, "--session-id", help="Resume a previous session"
    ),
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
    from petfish_bi_cli.semantic import load_all_metadata

    semantic_dir = Path("references") / "semantic"
    all_meta = load_all_metadata(semantic_dir)
    for meta in all_meta.values():
        typer.echo(f"  {meta.source_id} ({meta.source_type}): {meta.description}")


if __name__ == "__main__":
    app()
