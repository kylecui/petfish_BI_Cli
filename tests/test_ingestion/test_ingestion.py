from __future__ import annotations

from pathlib import Path

import pytest

from petfish_bi_cli.ingestion.crocs import parse_crocs_csv
from petfish_bi_cli.ingestion.jd import ProductRecord, parse_jd_json
from petfish_bi_cli.ingestion.tmall import parse_rose_jsonl, parse_tmall_jsonl

REFERENCES = Path(__file__).parent.parent.parent / "references"

_REAL_CROCS = REFERENCES / "CROCS_原始数据_20260605_144849.csv"
_REAL_JD = REFERENCES / "JD_CROCS_Raw_Memory_Dump.json"
_REAL_TMALL = REFERENCES / "TMALL_CROCS_Raw_Memory_Dump.json"
_REAL_ROSE = REFERENCES / "ROSE_10BRANDS_Raw_Dump.json"

has_real = _REAL_JD.exists()
real_skip = pytest.mark.skipif(not has_real, reason="Real data not available (gitignored)")


class TestCrocsCsvMock:
    def test_parses_mock_csv(self):
        records = parse_crocs_csv(REFERENCES / "mock_crocs_xiaohongshu.csv")
        assert len(records) > 0
        assert all(r.comment_text for r in records)

    def test_skips_empty_comments(self):
        records = parse_crocs_csv(REFERENCES / "mock_crocs_xiaohongshu.csv")
        assert all(r.comment_text.strip() for r in records)


@real_skip
class TestCrocsCsvReal:
    def test_parses_real_csv(self):
        records = parse_crocs_csv(_REAL_CROCS)
        assert len(records) > 100
        assert all(r.comment_text != "无" for r in records)


class TestJdJsonMock:
    def test_parses_mock_json(self):
        records = parse_jd_json(REFERENCES / "mock_jd_products.json")
        assert len(records) == 4
        assert all(isinstance(r, ProductRecord) for r in records)
        assert all(r.price > 0 for r in records)
        assert all(r.source == "jd_products" for r in records)

    def test_has_shop_names(self):
        records = parse_jd_json(REFERENCES / "mock_jd_products.json")
        assert all(r.shop for r in records)


@real_skip
class TestJdJsonReal:
    def test_parses_real_json(self):
        records = parse_jd_json(_REAL_JD)
        assert len(records) == 4


class TestTmallJsonlMock:
    def test_parses_mock_jsonl(self):
        records = parse_tmall_jsonl(REFERENCES / "mock_tmall_products.json")
        assert len(records) == 4
        assert all(isinstance(r.price, float) for r in records)
        assert all(r.source == "tmall_products" for r in records)


@real_skip
class TestTmallJsonlReal:
    def test_parses_real_jsonl(self):
        records = parse_tmall_jsonl(_REAL_TMALL)
        assert len(records) > 100

    def test_has_unique_shops(self):
        records = parse_tmall_jsonl(_REAL_TMALL)
        shops = {r.shop for r in records}
        assert len(shops) > 10


class TestRoseJsonlMock:
    def test_parses_mock_jsonl(self):
        records = parse_rose_jsonl(REFERENCES / "mock_rose_10brands.json")
        assert len(records) > 0
        assert all(r.source == "rose_10brands" for r in records)


@real_skip
class TestRoseJsonlReal:
    def test_parses_real_jsonl(self):
        records = parse_rose_jsonl(_REAL_ROSE)
        assert len(records) > 1000
