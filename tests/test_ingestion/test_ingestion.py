from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.ingestion.crocs import parse_crocs_csv
from petfish_bi_cli.ingestion.jd import ProductRecord, parse_jd_json
from petfish_bi_cli.ingestion.tmall import parse_rose_jsonl, parse_tmall_jsonl

REFERENCES = Path(__file__).parent.parent.parent / "references"


class TestCrocsCsv:
    def test_parses_real_csv(self):
        csv_path = REFERENCES / "CROCS_原始数据_20260605_144849.csv"
        records = parse_crocs_csv(csv_path)
        assert len(records) > 100
        assert all(r.comment_text for r in records)
        assert all(r.comment_text != "无" for r in records)

    def test_skips_empty_comments(self):
        csv_path = REFERENCES / "CROCS_原始数据_20260605_144849.csv"
        records = parse_crocs_csv(csv_path)
        assert all(r.comment_text.strip() for r in records)


class TestJdJson:
    def test_parses_real_json(self):
        json_path = REFERENCES / "JD_CROCS_Raw_Memory_Dump.json"
        records = parse_jd_json(json_path)
        assert len(records) == 4
        assert all(isinstance(r, ProductRecord) for r in records)
        assert all(r.price > 0 for r in records)
        assert all(r.source == "jd_products" for r in records)

    def test_has_shop_names(self):
        json_path = REFERENCES / "JD_CROCS_Raw_Memory_Dump.json"
        records = parse_jd_json(json_path)
        assert all(r.shop for r in records)


class TestTmallJsonl:
    def test_parses_real_jsonl(self):
        jsonl_path = REFERENCES / "TMALL_CROCS_Raw_Memory_Dump.json"
        records = parse_tmall_jsonl(jsonl_path)
        assert len(records) > 100
        assert all(isinstance(r.price, float) for r in records)
        assert all(r.source == "tmall_products" for r in records)

    def test_has_unique_shops(self):
        jsonl_path = REFERENCES / "TMALL_CROCS_Raw_Memory_Dump.json"
        records = parse_tmall_jsonl(jsonl_path)
        shops = {r.shop for r in records}
        assert len(shops) > 10


class TestRoseJsonl:
    def test_parses_real_jsonl(self):
        jsonl_path = REFERENCES / "ROSE_10BRANDS_Raw_Dump.json"
        records = parse_rose_jsonl(jsonl_path)
        assert len(records) > 1000

    def test_has_brand_extraction(self):
        jsonl_path = REFERENCES / "ROSE_10BRANDS_Raw_Dump.json"
        records = parse_rose_jsonl(jsonl_path)
        brands = {r.brand for r in records}
        assert len(brands) > 1
        assert "UNKNOWN" not in brands or len(brands) > 2

    def test_all_have_source(self):
        jsonl_path = REFERENCES / "ROSE_10BRANDS_Raw_Dump.json"
        records = parse_rose_jsonl(jsonl_path)
        assert all(r.source == "rose_10brands" for r in records)
