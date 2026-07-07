from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from petfish_bi_cli.ingestion.jd import ProductRecord


@dataclass(frozen=True)
class TimepointSnapshot:
    timestamp: str
    records: tuple[ProductRecord, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.records)

    @property
    def avg_price(self) -> float:
        prices = [r.price for r in self.records if r.price > 0]
        return round(sum(prices) / len(prices), 2) if prices else 0.0

    @property
    def price_range(self) -> tuple[float, float]:
        prices = [r.price for r in self.records if r.price > 0]
        if not prices:
            return (0.0, 0.0)
        return (min(prices), max(prices))


def _parse_jsonl_with_timepoints(file_path: Path) -> list[dict]:
    dumps: list[dict] = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = data.get("timestamp", data.get("crawl_time", data.get("time", "")))
            extracted = data.get("extracted_items", [])
            if isinstance(extracted, list) and extracted:
                dumps.append({"timestamp": str(ts), "items": extracted})
    return dumps


def parse_tmall_timepoints(file_path: Path) -> list[TimepointSnapshot]:
    dumps = _parse_jsonl_with_timepoints(file_path)
    snapshots: list[TimepointSnapshot] = []
    for dump in dumps:
        records = []
        for item in dump["items"]:
            price_str = str(item.get("price", "0"))
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                price = 0.0
            records.append(
                ProductRecord(
                    item_id=str(item.get("itemId", "")),
                    title=item.get("title", ""),
                    price=price,
                    shop=item.get("shop", ""),
                    source="tmall_products",
                )
            )
        snapshots.append(
            TimepointSnapshot(
                timestamp=dump["timestamp"],
                records=tuple(records),
            )
        )
    return snapshots


def parse_rose_timepoints(file_path: Path) -> list[TimepointSnapshot]:
    dumps = _parse_jsonl_with_timepoints(file_path)
    snapshots: list[TimepointSnapshot] = []
    for dump in dumps:
        records = []
        for item in dump["items"]:
            ump_price = item.get("ump_price", item.get("show_price", 0))
            try:
                price = float(ump_price)
            except (ValueError, TypeError):
                price = 0.0
            records.append(
                ProductRecord(
                    item_id=str(item.get("itemId", "")),
                    title=item.get("title", ""),
                    price=price,
                    shop=item.get("shop", ""),
                    source="rose_10brands",
                )
            )
        snapshots.append(
            TimepointSnapshot(
                timestamp=dump["timestamp"],
                records=tuple(records),
            )
        )
    return snapshots


def list_timepoints(source: str, data_root: Path) -> list[str]:
    if source == "tmall_products":
        path = data_root / "TMALL_CROCS_Raw_Memory_Dump.json"
        snaps = parse_tmall_timepoints(path)
    elif source == "rose_10brands":
        path = data_root / "ROSE_10BRANDS_Raw_Dump.json"
        snaps = parse_rose_timepoints(path)
    else:
        return []
    return [s.timestamp for s in snaps]
