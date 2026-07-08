from __future__ import annotations

import pytest

from petfish_bi_cli.domain import BIReport
from petfish_bi_cli.renderers.markdown import render, render_markdown


class TestMarkdownRenderer:
    def test_basic_render(self):
        report = BIReport(
            answer="CROCS均价561.01元",
            data={
                "findings": [
                    {"metric": "avg_price", "value": 561.01, "claim_id": "c1"}
                ]
            },
            session_id="ses_test",
            status="ok",
        )
        md = render_markdown(report, sources=["jd_products"])
        assert "561.01" in md
        assert "avg_price" in md
        assert "jd_products" in md

    def test_empty_findings(self):
        report = BIReport(
            answer="数据不足",
            data={},
            session_id="ses_empty",
            status="no_data",
        )
        md = render_markdown(report)
        assert "数据不足" in md
        assert "no_data" in md

    def test_render_dispatch(self):
        report = BIReport(
            answer="test",
            data={},
            session_id="s1",
            status="ok",
        )
        md = render(report, fmt="markdown")
        assert "test" in md

    def test_unknown_format_raises(self):
        report = BIReport(answer="t", data={}, status="ok")
        with pytest.raises(ValueError):
            render(report, fmt="pdf")

    def test_multiple_findings(self):
        report = BIReport(
            answer="JD 561.01, TMALL 421.16",
            data={
                "findings": [
                    {"metric": "jd_avg", "value": 561.01, "claim_id": "c1"},
                    {"metric": "tmall_avg", "value": 421.16, "claim_id": "c2"},
                ]
            },
            session_id="s2",
            status="ok",
        )
        md = render_markdown(report, sources=["jd_products", "tmall_products"])
        assert "561.01" in md
        assert "421.16" in md
        assert "jd_products" in md
        assert "tmall_products" in md

    def test_writes_to_file(self, tmp_path):
        report = BIReport(
            answer="test report",
            data={"findings": [{"metric": "m", "value": 1.0}]},
            session_id="s3",
            status="ok",
        )
        md = render_markdown(report)
        out = tmp_path / "report.md"
        out.write_text(md, encoding="utf-8")
        assert out.exists()
        assert "test report" in out.read_text(encoding="utf-8")
