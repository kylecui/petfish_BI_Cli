"""Tests for ReportRenderer — configurable output templates."""
from __future__ import annotations

import pytest

from petfish_bi_cli.rendering.renderer import ReportRenderer


@pytest.fixture
def sample_report():
    class FakeReport:
        answer = "CROCS在京东的均价是561.01元。"
        data = {
            "findings": [
                {"metric": "avg_price_jd", "value": 561.01, "claim_id": "c1"},
            ],
        }
        session_id = "test-session-001"

    return FakeReport()


@pytest.fixture
def sample_claims():
    class FakeClaims:
        claims = [
            type("C", (), {
                "id": "c1",
                "metric": "avg_price_jd",
                "value": 561.01,
                "source": "jd_products",
                "computation": "AVG(price) over 4 items",
            })(),
        ]
        def all_grounded_numbers(self):
            return {561.01}

    return FakeClaims()


class TestReportRenderer:
    def test_render_json_default(self, sample_report, sample_claims):
        renderer = ReportRenderer()
        output = renderer.render_json(sample_report, sample_claims)
        assert "avg_price_jd" in output
        assert "561.01" in output

    def test_render_markdown_default(self, sample_report, sample_claims):
        renderer = ReportRenderer()
        output = renderer.render_markdown(sample_report, sample_claims)
        assert "561.01" in output
        assert "avg_price_jd" in output or "avg_price" in output

    def test_render_html_default(self, sample_report, sample_claims):
        renderer = ReportRenderer()
        output = renderer.render_html(sample_report, sample_claims)
        assert "561.01" in output

    def test_custom_template_path(self, tmp_path, sample_report, sample_claims):
        tmpl = tmp_path / "custom.json.j2"
        tmpl.write_text('{"answer": "{{ report.answer }}", "claims": {{ claims.claims | length }}}')
        renderer = ReportRenderer(json_template=str(tmpl))
        output = renderer.render_json(sample_report, sample_claims)
        assert "CROCS" in output

    def test_grounding_not_affected(self, sample_report, sample_claims):
        renderer = ReportRenderer()
        renderer.render_json(sample_report, sample_claims)
        assert sample_report.data["findings"][0]["value"] == 561.01

    def test_no_config_uses_defaults(self):
        renderer = ReportRenderer()
        assert renderer is not None

    def test_render_unknown_format_raises(self, sample_report, sample_claims):
        renderer = ReportRenderer()
        with pytest.raises(ValueError):
            renderer.render(sample_report, sample_claims, fmt="xml")
