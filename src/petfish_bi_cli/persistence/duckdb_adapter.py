from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


class DuckDBAdapter:
    """Query raw files directly via DuckDB — no ingestion pipeline needed."""

    def __init__(self, data_root: Path | str = "references"):
        self._data_root = Path(data_root)
        self._con = duckdb.connect(":memory:")

    def query_csv(self, file_pattern: str, sql: str) -> list[dict[str, Any]]:
        path = str(self._data_root / file_pattern)
        full_sql = sql.replace("{TABLE}", f"read_csv_auto('{path}')")
        return self._fetch(full_sql)

    def query_json(self, file_pattern: str, sql: str) -> list[dict[str, Any]]:
        path = str(self._data_root / file_pattern)
        full_sql = sql.replace("{TABLE}", f"read_json_auto('{path}')")
        return self._fetch(full_sql)

    def query_jsonl(self, file_pattern: str, sql: str) -> list[dict[str, Any]]:
        path = str(self._data_root / file_pattern)
        full_sql = sql.replace(
            "{TABLE}",
            f"read_json_auto('{path}', format='newline_delimited', ignore_errors=true)",
        )
        return self._fetch(full_sql)

    def raw_sql(self, sql: str) -> list[dict[str, Any]]:
        return self._fetch(sql)

    def avg_price_csv(self, file_pattern: str, price_col: str = "price") -> float:
        rows = self.query_csv(
            file_pattern,
            f"SELECT AVG(CAST({price_col} AS DOUBLE)) AS avg FROM {{TABLE}}",
        )
        return float(rows[0]["avg"]) if rows and rows[0]["avg"] else 0.0

    def avg_price_jsonl(
        self, file_pattern: str, price_col: str = "price"
    ) -> float:
        rows = self.query_jsonl(
            file_pattern,
            f"SELECT AVG(CAST({price_col} AS DOUBLE)) AS avg FROM {{TABLE}}",
        )
        return float(rows[0]["avg"]) if rows and rows[0]["avg"] else 0.0

    def count_csv(self, file_pattern: str) -> int:
        rows = self.query_csv(file_pattern, "SELECT COUNT(*) AS cnt FROM {TABLE}")
        return int(rows[0]["cnt"]) if rows else 0

    def count_jsonl(self, file_pattern: str) -> int:
        rows = self.query_jsonl(file_pattern, "SELECT COUNT(*) AS cnt FROM {TABLE}")
        return int(rows[0]["cnt"]) if rows else 0

    def _fetch(self, sql: str) -> list[dict[str, Any]]:
        result = self._con.execute(sql)
        cols = [d[0] for d in result.description]
        return [dict(zip(cols, row, strict=False)) for row in result.fetchall()]

    def close(self) -> None:
        self._con.close()
