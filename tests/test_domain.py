from __future__ import annotations

from petfish_bi_cli.domain import BIQuery, BIReport


class TestBIQuery:
    def test_frozen(self):
        q = BIQuery(prompt="test")
        try:
            q.prompt = "changed"
            raise AssertionError("Should have failed")
        except AttributeError:
            pass

    def test_defaults(self):
        q = BIQuery(prompt="test")
        assert q.data_sources == ()
        assert q.metadata == {}


class TestBIReport:
    def test_frozen(self):
        r = BIReport(answer="test")
        try:
            r.status = "error"
            raise AssertionError("Should have failed")
        except AttributeError:
            pass

    def test_defaults(self):
        r = BIReport(answer="result")
        assert r.data == {}
        assert r.status == "ok"
        assert r.session_id == ""
        assert r.rich_content is None

    def test_with_findings(self):
        r = BIReport(
            answer="avg price is 424.0",
            data={"findings": [{"metric": "avg_price", "value": 424.0, "claim_id": "c1"}]},
        )
        assert r.data["findings"][0]["claim_id"] == "c1"
