from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.persistence.duckdb_adapter import DuckDBAdapter

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestDuckDBAdapterCSV:
    def test_count_csv(self):
        db = DuckDBAdapter(DATA_ROOT)
        count = db.count_csv("CROCS_*.csv")
        assert count > 100
        db.close()

    def test_query_csv_returns_dicts(self):
        db = DuckDBAdapter(DATA_ROOT)
        rows = db.query_csv(
            "CROCS_*.csv",
            "SELECT COUNT(*) AS cnt FROM {TABLE}",
        )
        assert len(rows) == 1
        assert "cnt" in rows[0]
        assert rows[0]["cnt"] > 0
        db.close()


class TestDuckDBAdapterJSONL:
    def test_count_jsonl_tmall(self):
        db = DuckDBAdapter(DATA_ROOT)
        count = db.count_jsonl("TMALL_CROCS_Raw_Memory_Dump.json")
        assert count > 0
        db.close()

    def test_count_jsonl_rose(self):
        db = DuckDBAdapter(DATA_ROOT)
        count = db.count_jsonl("ROSE_10BRANDS_Raw_Dump.json")
        assert count > 0
        db.close()


class TestDuckDBAdapterRawSQL:
    def test_raw_sql(self):
        db = DuckDBAdapter(DATA_ROOT)
        rows = db.raw_sql("SELECT 42 AS answer")
        assert rows == [{"answer": 42}]
        db.close()

    def test_cross_source_join(self):
        db = DuckDBAdapter(DATA_ROOT)
        jd_path = str(DATA_ROOT / "JD_CROCS_Raw_Memory_Dump.json")
        rows = db.raw_sql(
            f"SELECT COUNT(*) AS cnt FROM read_json_auto('{jd_path}')"
        )
        assert rows[0]["cnt"] > 0
        db.close()


class TestDuckDBAdapterLifecycle:
    def test_close_does_not_crash(self):
        db = DuckDBAdapter(DATA_ROOT)
        db.close()

    def test_multiple_queries_same_connection(self):
        db = DuckDBAdapter(DATA_ROOT)
        db.raw_sql("SELECT 1")
        db.raw_sql("SELECT 2")
        db.close()
