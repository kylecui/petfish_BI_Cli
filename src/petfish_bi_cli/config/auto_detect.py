"""Auto-detection for data source format and schema inference."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def detect_format(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext == ".jsonl":
        return "jsonl"
    if ext == ".json":
        with open(path, encoding="utf-8") as f:
            first = f.readline().strip()
            if not first:
                return "json"
            second = f.readline().strip()
            if second and second.startswith("{"):
                return "jsonl"
        return "json"
    with open(path, encoding="utf-8", errors="ignore") as f:
        sample = f.read(2048)
    try:
        json.loads(sample)
        return "json"
    except (json.JSONDecodeError, ValueError):
        if "," in sample and "\n" in sample:
            return "csv"
    raise ValueError(f"Cannot detect format for {path}")


def infer_metrics(path: Path, source_type: str) -> list[dict[str, Any]]:
    if source_type == "csv":
        return _infer_csv_metrics(path)
    if source_type in ("json", "jsonl"):
        return _infer_json_metrics(path, source_type)
    return [{"name": "item_count", "aggregation": "count"}]


def _is_numeric(val: str) -> bool:
    if not val or not val.strip():
        return False
    try:
        float(val)
        return True
    except ValueError:
        return False


def _infer_csv_metrics(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(row for _, row in zip(range(20), reader, strict=False))
    metrics: list[dict[str, Any]] = []
    for h in headers:
        values = [r.get(h, "") for r in rows]
        non_empty = [v for v in values if v and v.strip()]
        if non_empty and all(_is_numeric(v) for v in non_empty):
            metrics.append({"name": h, "column": h, "aggregation": "avg"})
    if not metrics:
        metrics.append({"name": "row_count", "aggregation": "count"})
    return metrics


def _infer_json_metrics(path: Path, source_type: str) -> list[dict[str, Any]]:
    items = _extract_json_items(path, source_type)
    if not items:
        return [{"name": "item_count", "aggregation": "count"}]
    first = items[0]
    if not isinstance(first, dict):
        return [{"name": "item_count", "aggregation": "count"}]
    metrics: list[dict[str, Any]] = []
    for key, val in first.items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            metrics.append({"name": key, "column": key, "aggregation": "avg"})
    if not metrics:
        metrics.append({"name": "item_count", "aggregation": "count"})
    return metrics


def _extract_json_items(path: Path, source_type: str) -> list[dict]:
    if source_type == "jsonl":
        items: list[dict] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                extracted = data.get("extracted_items", [])
                if isinstance(extracted, list):
                    items.extend(extracted)
                elif isinstance(data, dict):
                    items.append(data)
        return items
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    results = data.get("raw_data", {}).get("search_results", [])
    if not results:
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                results = v
                break
    if not results and isinstance(data, dict):
        results = [data]
    return results if isinstance(results, list) else []
