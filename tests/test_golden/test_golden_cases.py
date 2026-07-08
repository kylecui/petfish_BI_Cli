from __future__ import annotations

import os

import pytest

from petfish_bi_cli.domain import BIQuery
from petfish_bi_cli.grounding.claims import Claim, ClaimsLedger
from petfish_bi_cli.grounding.validator import validate_report

GOLDEN_CASES = [
    {
        "name": "jd_avg_price_lookup",
        "query": "CROCS在京东的均价是多少？",
        "intent": "lookup",
        "expected_status": "ok",
        "expected_keywords": ["561"],
        "expected_data_metrics": ["avg_price"],
    },
    {
        "name": "tmall_vs_jd_comparison",
        "query": "CROCS在京东和天猫的价格差异",
        "intent": "comparison",
        "expected_status": "ok",
        "expected_keywords": ["561", "421"],
        "expected_data_metrics": ["avg_price", "price_diff"],
    },
    {
        "name": "tmall_shop_count",
        "query": "天猫CROCS有多少家店铺？",
        "intent": "lookup",
        "expected_status": "ok",
        "expected_keywords": [],
        "expected_data_metrics": ["shop_count"],
    },
    {
        "name": "insufficient_data_handling",
        "query": "CROCS在拼多多的销量是多少？",
        "intent": "lookup",
        "expected_status": "no_data",
        "expected_keywords": [],
        "expected_data_metrics": [],
    },
]


@pytest.fixture
def fake_ledger():
    c1 = Claim(id="c1", metric="avg_price", value=424.0, source="jd_products")
    c2 = Claim(id="c2", metric="avg_price", value=407.01, source="tmall_products")
    c3 = Claim(id="c3", metric="shop_count", value=87.0, source="tmall_products")
    return ClaimsLedger(claims=(c1, c2, c3))


class TestGoldenCaseDefinition:
    """Golden cases are defined here. Run with real model to validate."""

    def test_golden_cases_count(self):
        assert len(GOLDEN_CASES) == 4

    def test_each_case_has_required_fields(self):
        required = {"name", "query", "intent", "expected_status"}
        for case in GOLDEN_CASES:
            assert required.issubset(case.keys()), f"Case {case.get('name')} missing fields"

    def test_intents_are_diverse(self):
        intents = {c["intent"] for c in GOLDEN_CASES}
        assert "lookup" in intents
        assert "comparison" in intents

    def test_expected_statuses_are_valid(self):
        valid_statuses = {"ok", "no_data", "budget_exceeded", "validation_failed", "parse_error"}
        for case in GOLDEN_CASES:
            assert case["expected_status"] in valid_statuses


class TestGroundingValidation:
    """Test that grounding validator catches fabricated claims."""

    def test_valid_claim_passes(self, fake_ledger):
        result = validate_report(
            report_answer="均价424.0元",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=fake_ledger,
        )
        assert result.valid

    def test_fabricated_number_rejected(self, fake_ledger):
        result = validate_report(
            report_answer="均价424.0元，销量超过10000件",
            report_data={"findings": [{"value": 424.0, "claim_id": "c1"}]},
            claims=fake_ledger,
        )
        assert not result.valid

    def test_wrong_claim_value_rejected(self, fake_ledger):
        result = validate_report(
            report_answer="均价424.0元",
            report_data={"findings": [{"value": 999.0, "claim_id": "c1"}]},
            claims=fake_ledger,
        )
        assert not result.valid


@pytest.mark.integration
class TestGoldenCasesWithRealModel:
    """Run golden cases against real model. Requires OPENAI_API_KEY or equivalent.

    Run: uv run pytest tests/test_golden/test_golden_cases.py -m integration -v
    """

    @pytest.fixture(autouse=True)
    def _load_env(self):
        from dotenv import load_dotenv

        load_dotenv(override=True)
        key = os.environ.get("BI_CLI_MODEL_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            pytest.skip("No API key in .env or env vars")
        yield

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["name"] for c in GOLDEN_CASES])
    def test_golden_case(self, case):
        from petfish_bi_cli.application import BIApplication

        app = BIApplication()
        query = BIQuery(prompt=case["query"])
        report = app.execute(query)

        assert report.status == case["expected_status"], (
            f"Case '{case['name']}': expected status '{case['expected_status']}', "
            f"got '{report.status}'. Answer: {report.answer}"
        )

        for keyword in case.get("expected_keywords", []):
            assert keyword in (report.answer or "") or keyword in str(report.data), (
                f"Case '{case['name']}': keyword '{keyword}' not found in output"
            )
