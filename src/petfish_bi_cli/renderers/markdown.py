from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


def render_markdown(
    report: Any,
    sources: list[str] | None = None,
) -> str:
    template = _get_env().get_template("bi_report.md.j2")
    return template.render(
        report=report,
        sources=sources or [],
        timestamp=date.today().isoformat(),
    )


def render_html(
    report: Any,
    sources: list[str] | None = None,
) -> str:
    template = _get_env().get_template("bi_report.html.j2")
    return template.render(
        report=report,
        sources=sources or [],
        timestamp=date.today().isoformat(),
    )


def render(
    report: Any,
    fmt: str = "markdown",
    sources: list[str] | None = None,
) -> str:
    if fmt == "markdown":
        return render_markdown(report, sources)
    elif fmt == "html":
        return render_html(report, sources)
    raise ValueError(f"Unknown format: {fmt}")
