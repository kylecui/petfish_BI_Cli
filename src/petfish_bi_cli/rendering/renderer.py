"""ReportRenderer — configurable output templates with Jinja2."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

_DEFAULT_JSON_TEMPLATE = Template(
    '{\n'
    '  "answer": {{ report.answer | tojson }},\n'
    '  "findings": {{ report.data.findings | tojson }},\n'
    '  "session_id": {{ report.session_id | tojson }}\n'
    '}'
)

_DEFAULT_MARKDOWN_TEMPLATE = Template(
    '## BI Report\n\n'
    '{{ report.answer }}\n\n'
    '{% if report.data and report.data.findings %}'
    '### Findings\n\n'
    '{% for f in report.data.findings %}'
    '- **{{ f.metric }}**: {{ f.value }} (claim: {{ f.claim_id }})\n'
    '{% endfor %}'
    '{% endif %}'
)

_DEFAULT_HTML_TEMPLATE = Template(
    '<html><body>\n'
    '<h1>BI Report</h1>\n'
    '<p>{{ report.answer }}</p>\n'
    '{% if report.data and report.data.findings %}'
    '<h2>Findings</h2>\n<ul>\n'
    '{% for f in report.data.findings %}'
    '<li><strong>{{ f.metric }}</strong>: {{ f.value }}</li>\n'
    '{% endfor %}'
    '</ul>\n{% endif %}\n'
    '</body></html>'
)


class ReportRenderer:
    """Renders BIReport to JSON/Markdown/HTML using configurable Jinja2 templates."""

    def __init__(
        self,
        json_template: str | None = None,
        markdown_template: str | None = None,
        html_template: str | None = None,
    ):
        self._json_path = json_template
        self._md_path = markdown_template
        self._html_path = html_template
        self._env: Environment | None = None

    def _get_env(self) -> Environment:
        if self._env is None:
            self._env = Environment(autoescape=select_autoescape(["html"]))
            paths = [
                Path(p).parent for p in [self._json_path, self._md_path, self._html_path] if p
            ]
            if paths:
                self._env.loader = FileSystemLoader([str(p) for p in paths])
        return self._env

    def _load_template(self, path: str | None, default: Template) -> Template:
        if path and Path(path).exists():
            return self._get_env().get_template(Path(path).name)
        return default

    def render_json(self, report: Any, claims: Any) -> str:
        tmpl = self._load_template(self._json_path, _DEFAULT_JSON_TEMPLATE)
        return tmpl.render(report=report, claims=claims)

    def render_markdown(self, report: Any, claims: Any) -> str:
        tmpl = self._load_template(self._md_path, _DEFAULT_MARKDOWN_TEMPLATE)
        return tmpl.render(report=report, claims=claims)

    def render_html(self, report: Any, claims: Any) -> str:
        tmpl = self._load_template(self._html_path, _DEFAULT_HTML_TEMPLATE)
        return tmpl.render(report=report, claims=claims)

    def render(self, report: Any, claims: Any, fmt: str = "json") -> str:
        if fmt == "json":
            return self.render_json(report, claims)
        if fmt == "markdown":
            return self.render_markdown(report, claims)
        if fmt == "html":
            return self.render_html(report, claims)
        raise ValueError(f"Unknown format: {fmt}")
