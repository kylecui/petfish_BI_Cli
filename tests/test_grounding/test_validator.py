from __future__ import annotations

from petfish_bi_cli.grounding.claims import Claim, ClaimsLedger
from petfish_bi_cli.grounding.validator import validate_report


class TestValidateReport:
    def test_valid_report(self):
        c1 = Claim(id="c1", metric="avg_price", value=489.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report(
            report_answer="CROCS均价489.0元",
            report_data={"findings": [{"metric": "avg_price", "value": 489.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is True
        assert result.errors == ()

    def test_unverified_number_in_answer(self):
        c1 = Claim(id="c1", metric="avg_price", value=489.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report(
            report_answer="CROCS均价489.0元，环比增长15.3%",
            report_data={"findings": [{"value": 489.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("15.3" in e for e in result.errors)

    def test_value_mismatch(self):
        c1 = Claim(id="c1", metric="avg_price", value=489.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report(
            report_answer="均价489.0",
            report_data={"findings": [{"metric": "avg_price", "value": 999.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("mismatch" in e for e in result.errors)

    def test_finding_without_claim_id(self):
        c1 = Claim(id="c1", metric="price", value=100.0, source="s")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report(
            report_answer="100.0",
            report_data={"findings": [{"metric": "unknown", "value": 42.0}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("unverified" in e for e in result.errors)

    def test_empty_findings_valid(self):
        ledger = ClaimsLedger()
        result = validate_report(
            report_answer="数据不足",
            report_data={},
            claims=ledger,
        )
        assert result.valid is True

    def test_two_claims_comparison(self):
        c1 = Claim(id="c1", metric="jd_price", value=489.0, source="jd")
        c2 = Claim(id="c2", metric="tmall_price", value=407.01, source="tmall")
        c3 = Claim(id="c3", metric="diff", value=81.99, source="analyze")
        ledger = ClaimsLedger(claims=(c1, c2, c3))
        result = validate_report(
            report_answer="JD均价489.0，TMALL均价407.01，差81.99",
            report_data={"findings": [
                {"value": 489.0, "claim_id": "c1"},
                {"value": 407.01, "claim_id": "c2"},
                {"value": 81.99, "claim_id": "c3"},
            ]},
            claims=ledger,
        )
        assert result.valid is True
