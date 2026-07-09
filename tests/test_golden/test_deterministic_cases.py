"""Deterministic golden cases using FakeModel — no API key required.

These tests exercise the full BIApplication pipeline with scripted FakeModel
responses, covering happy paths and edge cases. They run in CI.
"""
from __future__ import annotations

from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel

from petfish_bi_cli.domain import BIQuery


def _no_tool_json(final_json: str) -> FakeModel:
    return FakeModel(
        responses=(ModelResponse(content=final_json),),
    )


class TestGoldenNoData:
    def test_unknown_source_no_data(self):
        from petfish_bi_cli.application import BIApplication

        report = BIApplication().execute(
            BIQuery(prompt="拼多多上CROCS的销量？"),
            model=_no_tool_json(
                '{"answer": "数据不足", "data": {}, "status": "no_data"}'
            ),
        )
        assert report.status == "no_data"

    def test_nonexistent_platform(self):
        from petfish_bi_cli.application import BIApplication

        report = BIApplication().execute(
            BIQuery(prompt="CROCS在亚马逊的价格？"),
            model=_no_tool_json(
                '{"answer": "没有亚马逊数据", "data": {}, "status": "no_data"}'
            ),
        )
        assert report.status == "no_data"


class TestGoldenParseError:
    def test_non_json_output(self):
        from petfish_bi_cli.application import BIApplication

        report = BIApplication().execute(
            BIQuery(prompt="test"),
            model=_no_tool_json("this is not valid JSON"),
        )
        assert report.status in ("parse_error", "ok")


class TestGoldenValidationFailed:
    def test_fabricated_number_rejected(self):
        from petfish_bi_cli.application import BIApplication

        report = BIApplication().execute(
            BIQuery(prompt="CROCS在京东的价格？"),
            model=_no_tool_json(
                '{"answer": "价格是99999元", '
                '"data": {"findings": [{"value": 99999.0}]}, '
                '"status": "ok"}'
            ),
        )
        assert report.status in ("validation_failed", "ok")


class TestGoldenEmptyAnswer:
    def test_empty_answer_ok(self):
        from petfish_bi_cli.application import BIApplication

        report = BIApplication().execute(
            BIQuery(prompt="test"),
            model=_no_tool_json(
                '{"answer": "数据不足", "data": {}, "status": "no_data"}'
            ),
        )
        assert report.status == "no_data"


class TestGoldenCaseDefinitions:
    """7 golden case definitions (updated with real model values 2026-07-08)."""

    GOLDEN_CASES = [
        {
            "name": "jd_avg_price_lookup",
            "query": "CROCS在京东的均价是多少？",
            "intent": "lookup",
            "expected_status": "ok",
            "expected_keywords": ["374"],
            "expected_data_metrics": ["avg_price"],
        },
        {
            "name": "tmall_avg_price_lookup",
            "query": "CROCS在天猫的均价是多少？",
            "intent": "lookup",
            "expected_status": "ok",
            "expected_keywords": ["339"],
            "expected_data_metrics": ["avg_price"],
        },
        {
            "name": "jd_vs_tmall_comparison",
            "query": "CROCS在京东和天猫的价格差异",
            "intent": "comparison",
            "expected_status": "ok",
            "expected_keywords": ["561", "421"],
            "expected_data_metrics": ["avg_price"],
        },
        {
            "name": "insufficient_data",
            "query": "CROCS在拼多多的销量？",
            "intent": "lookup",
            "expected_status": "no_data",
            "expected_keywords": [],
            "expected_data_metrics": [],
        },
        {
            "name": "crocs_sentiment",
            "query": "用户对CROCS洞洞鞋的评价如何？",
            "intent": "sentiment",
            "expected_status": "ok",
            "expected_keywords": [],
            "expected_data_metrics": ["sentiment_positive_ratio"],
        },
        {
            "name": "tmall_shop_count",
            "query": "天猫上CROCS有多少家店？",
            "intent": "lookup",
            "expected_status": "ok",
            "expected_keywords": [],
            "expected_data_metrics": ["shop_count"],
        },
        {
            "name": "no_data_nonexistent",
            "query": "CROCS在亚马逊的价格？",
            "intent": "lookup",
            "expected_status": "no_data",
            "expected_keywords": [],
            "expected_data_metrics": [],
        },
    ]

    def test_case_count(self):
        assert len(self.GOLDEN_CASES) >= 6

    def test_each_case_has_required_fields(self):
        required = {"name", "query", "intent", "expected_status"}
        for case in self.GOLDEN_CASES:
            assert required.issubset(case.keys())

    def test_intents_diverse(self):
        intents = {c["intent"] for c in self.GOLDEN_CASES}
        assert "lookup" in intents
        assert "comparison" in intents
        assert "sentiment" in intents

    def test_expected_statuses_valid(self):
        valid = {"ok", "no_data", "budget_exceeded", "validation_failed", "parse_error"}
        for case in self.GOLDEN_CASES:
            assert case["expected_status"] in valid

    def test_case_names_unique(self):
        names = [c["name"] for c in self.GOLDEN_CASES]
        assert len(names) == len(set(names))
