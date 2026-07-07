from __future__ import annotations

from petfish_bi_cli.grounding.claims import Claim, ClaimsLedger
from petfish_bi_cli.grounding.enhanced_validator import (
    cn_to_num,
    extract_numbers,
    validate_report_enhanced,
)


class TestCnToNum:
    def test_arabic(self):
        assert cn_to_num("424") == 424.0

    def test_decimal(self):
        assert cn_to_num("424.5") == 424.5

    def test_chinese_simple(self):
        assert cn_to_num("四百二十四") == 424.0

    def test_chinese_ten(self):
        assert cn_to_num("十") == 10.0

    def test_chinese_hundred(self):
        assert cn_to_num("一百") == 100.0

    def test_invalid(self):
        assert cn_to_num("abc") is None

    def test_empty(self):
        assert cn_to_num("") is None


class TestExtractNumbers:
    def test_arabic_numbers(self):
        nums = extract_numbers("均价424.0元，差价16.99元")
        assert 424.0 in nums
        assert 16.99 in nums

    def test_comma_numbers(self):
        nums = extract_numbers("共1,275条记录")
        assert 1275.0 in nums

    def test_chinese_numbers(self):
        nums = extract_numbers("均价四百二十四元")
        assert 424.0 in nums

    def test_mixed(self):
        nums = extract_numbers("JD均价424.0，TMALL四百零七")
        assert 424.0 in nums

    def test_no_numbers(self):
        assert extract_numbers("没有数字") == []


class TestValidateReportEnhanced:
    def test_valid_report(self):
        c1 = Claim(id="c1", metric="avg_price", value=424.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="均价424.0元",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is True
        assert len(result.verified_numbers) >= 1

    def test_fabricated_number(self):
        c1 = Claim(id="c1", metric="avg", value=424.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="均价424.0元，环比增长15.3%",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("15.3" in e for e in result.errors)

    def test_approximate_match_t2(self):
        c1 = Claim(id="c1", metric="avg", value=424.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="均价约425元",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert 425.0 in result.verified_numbers

    def test_truth_labels(self):
        c1 = Claim(id="c1", metric="avg", value=100.0, source="s")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="100.0",
            report_data={"findings": [{"value": 100.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert any("T1:" in label for label in result.truth_labels)

    def test_chinese_number_in_answer(self):
        c1 = Claim(id="c1", metric="avg", value=424.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="均价四百二十四元",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert 424.0 in result.verified_numbers

    def test_unknown_claim_id(self):
        c1 = Claim(id="c1", metric="avg", value=100.0, source="s")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="100.0",
            report_data={"findings": [{"value": 100.0, "claim_id": "c999"}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("c999" in e for e in result.errors)

    def test_empty_report_valid(self):
        ledger = ClaimsLedger()
        result = validate_report_enhanced(
            report_answer="数据不足",
            report_data={},
            claims=ledger,
        )
        assert result.valid is True

    def test_value_mismatch(self):
        c1 = Claim(id="c1", metric="avg", value=424.0, source="jd")
        ledger = ClaimsLedger(claims=(c1,))
        result = validate_report_enhanced(
            report_answer="424.0",
            report_data={"findings": [{"value": 999.0, "claim_id": "c1"}]},
            claims=ledger,
        )
        assert result.valid is False
        assert any("mismatch" in e for e in result.errors)
