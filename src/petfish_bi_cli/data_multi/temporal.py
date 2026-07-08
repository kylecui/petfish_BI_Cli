from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from petfish_bi_cli.ingestion import (
    parse_crocs_csv,
)


class TemporalDataLoader:
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    def load(self, source: str) -> list[dict[str, Any]]:
        if source == "jd_products":
            return self._load_jd()
        elif source == "tmall_products":
            return self._load_tmall()
        elif source == "crocs_xiaohongshu":
            return self._load_crocs()
        elif source == "rose_10brands":
            return self._load_rose()
        return []

    def _load_jd(self) -> list[dict[str, Any]]:
        path = self.data_root / "JD_CROCS_Raw_Memory_Dump.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        results = []
        raw = data.get("raw_data", data) if isinstance(data, dict) else data
        items = raw.get("search_results", []) if isinstance(raw, dict) else raw
        for item in items:
            results.append(
                {
                    "source": "jd_products",
                    "price": float(item.get("calculatedFinalPrice", 0)),
                    "title": item.get("skuName", ""),
                    "shop": item.get("shopName", ""),
                    "timestamp": data.get("timestamp", 0) if isinstance(data, dict) else 0,
                }
            )
        return results

    def _load_tmall(self) -> list[dict[str, Any]]:
        path = self.data_root / "TMALL_CROCS_Raw_Memory_Dump.json"
        if not path.exists():
            return []
        results = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                dump = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_raw = dump.get("timestamp", 0)
            ts = self._parse_time(str(ts_raw)) if isinstance(ts_raw, str) else float(ts_raw)
            items = dump.get("extracted_items", [])
            for item in items:
                results.append(
                    {
                        "source": "tmall_products",
                        "price": float(item.get("price", 0)),
                        "title": item.get("title", ""),
                        "shop": item.get("shop", ""),
                        "timestamp": ts,
                    }
                )
        return results

    def _load_crocs(self) -> list[dict[str, Any]]:
        path = self.data_root / "CROCS_原始数据_20260605_144849.csv"
        if not path.exists():
            return []
        records = parse_crocs_csv(path)
        results = []
        for r in records:
            results.append(
                {
                    "source": "crocs_xiaohongshu",
                    "content": r.comment_text,
                    "search_keyword": r.search_keyword,
                    "note_title": r.note_title,
                    "comment_time": r.comment_time,
                    "timestamp": self._parse_time(r.comment_time),
                }
            )
        return results

    def _load_rose(self) -> list[dict[str, Any]]:
        path = self.data_root / "ROSE_10BRANDS_Raw_Dump.json"
        if not path.exists():
            return []
        results = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                dump = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = dump.get("timestamp", 0)
            items = dump.get("extracted_items", [])
            for item in items:
                results.append(
                    {
                        "source": "rose_10brands",
                        "price": float(item.get("ump_price", 0)),
                        "title": item.get("title", ""),
                        "shop": item.get("shop", ""),
                        "brand": item.get("brand", ""),
                        "timestamp": ts,
                    }
                )
        return results

    def _parse_time(self, time_str: str) -> float:
        if not time_str:
            return 0.0
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(time_str.strip(), fmt).timestamp()
            except ValueError:
                continue
        return 0.0

    def get_timestamps(self, source: str) -> list[float]:
        records = self.load(source)
        return [float(r["timestamp"]) for r in records if float(r.get("timestamp", 0)) > 0]

    def compare_periods(self, source: str, metric: str, period: str = "day") -> dict[str, Any]:
        records = self.load(source)
        timestamps = [r["timestamp"] for r in records if float(r.get("timestamp", 0)) > 0]
        if not timestamps:
            return {"periods": {}, "metric": metric}
        groups = TimeSlice.group(timestamps, period=period)
        result: dict[str, Any] = {"periods": {}, "metric": metric}
        for label, indices in groups.items():
            period_records = [records[i] for i in indices if i < len(records)]
            values = [float(r.get(metric, r.get("price", 0))) for r in period_records]
            values = [v for v in values if isinstance(v, (int, float)) and v > 0]
            if values:
                result["periods"][label] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        if len(result["periods"]) >= 2:
            labels = sorted(result["periods"].keys())
            p1, p2 = result["periods"][labels[0]], result["periods"][labels[-1]]
            result["comparisons"] = {
                "first_vs_last": {
                    "avg_diff": round(p2["avg"] - p1["avg"], 2),
                    "avg_pct": round(
                        abs(p2["avg"] - p1["avg"]) / min(p1["avg"], p2["avg"]) * 100, 1
                    )
                    if min(p1["avg"], p2["avg"]) > 0
                    else 0,
                },
            }
        return result

    def trend(self, source: str, metric: str, period: str = "day") -> list[dict[str, Any]]:
        comparison = self.compare_periods(source, metric, period)
        periods = comparison.get("periods", {})
        return [{"label": label, **stats} for label, stats in sorted(periods.items())]


class TimeSlice:
    def __init__(self, period: str, timestamp: float):
        self.period = period
        self.timestamp = timestamp
        self.label = self._compute_label()

    def _compute_label(self) -> str:
        dt = datetime.fromtimestamp(self.timestamp)
        if self.period == "day":
            return dt.strftime("%Y-%m-%d")
        elif self.period == "week":
            return dt.strftime("%Y-W%U")
        elif self.period == "month":
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def group(timestamps: list[float], period: str = "day") -> dict[str, list[int]]:
        groups: dict[str, list[int]] = {}
        for i, ts in enumerate(timestamps):
            if float(ts) <= 0:
                continue
            slice_obj = TimeSlice(period=period, timestamp=ts)
            groups.setdefault(slice_obj.label, []).append(i)
        return groups
