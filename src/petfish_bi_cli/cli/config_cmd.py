"""Interactive config wizard — generates configs/bi_cli.yml from user input."""
from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

config_app = typer.Typer(help="Configuration management")


@config_app.command()
def init(
    output: Path = typer.Option(
        Path("configs/bi_cli.yml"), "--output", "-o", help="Output config file path"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
):
    """Initialize a new configuration file interactively."""
    if output.exists() and not force:
        typer.echo(f"Config already exists at {output}. Use --force to overwrite.")
        raise typer.Exit(1)

    typer.echo("=== petfish BI CLI Configuration Wizard ===\n")

    provider = typer.prompt(
        "Model provider",
        default="fake",
        show_default=True,
    )

    model_name = "fake"
    if provider != "fake":
        model_name = typer.prompt("Model name", default="gpt-4o")

    data_root = typer.prompt("Data root directory", default="references")

    typer.echo("\nScanning for data files...")
    sources = _scan_data_dir(Path(data_root))
    if sources:
        typer.echo(f"Found {len(sources)} data file(s):")
        for sid, info in sources.items():
            typer.echo(f"  {sid} ({info['type']}): {info['path']}")
        include = typer.confirm("Include these as data sources?", default=True)
        if not include:
            sources = {}
    else:
        typer.echo("No CSV/JSON files found in data root.")

    enable_web = typer.confirm("Enable web API server?", default=True)

    config = _build_config(
        provider=provider,
        model_name=model_name,
        data_root=data_root,
        sources=sources,
        enable_web=enable_web,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    typer.echo(f"\nConfig written to {output}")
    typer.echo("Run 'petfish-bi health' to verify.")


@config_app.command()
def show():
    """Display current configuration."""
    from petfish_bi_cli.config.settings import load_settings

    settings = load_settings()
    typer.echo(
        json.dumps(
            {
                "model": {"provider": settings.model.provider, "name": settings.model.name},
                "data": {"root": settings.data.root},
                "sources_count": len(settings.raw.get("sources", {})),
                "scripts_count": len(settings.raw.get("scripts", {})),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _scan_data_dir(data_root: Path) -> dict[str, dict]:
    sources: dict[str, dict] = {}
    if not data_root.exists():
        return sources

    for f in sorted(data_root.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in (".csv", ".json", ".jsonl"):
            continue
        source_id = f.stem.lower().replace("-", "_").replace(" ", "_")
        sources[source_id] = {
            "type": "csv" if ext == ".csv" else "json",
            "path": str(f.relative_to(data_root)),
            "description": f.stem,
        }
    return sources


def _build_config(
    provider: str,
    model_name: str,
    data_root: str,
    sources: dict[str, dict],
    enable_web: bool,
) -> dict:
    config: dict = {
        "model": {
            "provider": provider,
            "name": model_name,
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        "budget": {
            "max_tokens_per_session": 100000,
            "max_cost_usd": 0.50,
            "max_steps": 25,
        },
        "data": {
            "root": data_root,
            "semantic_dir": f"{data_root}/semantic",
        },
    }

    if sources:
        config["sources"] = sources

    if enable_web:
        config["_web_enabled"] = True

    return config
