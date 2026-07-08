from __future__ import annotations

import json
from pathlib import Path

from petfish_bi_cli.ingestion.jd import ProductRecord


def _parse_jsonl(file_path: Path) -> list[dict]:
    items: list[dict] = []
    with open(file_path, encoding="utf-8") as f:
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
    return items


def parse_tmall_jsonl(file_path: Path) -> list[ProductRecord]:
    items = _parse_jsonl(file_path)
    records: list[ProductRecord] = []
    for item in items:
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
    return records


_KNOWN_BRANDS = [
    "CROCS",
    "Crocs",
    "HUGO BOSS",
    "BOSS",
    "Adidas",
    "adidas",
    "ADIDAS",
    "Anta",
    "ANTA",
    "UGG",
    "ugg",
    "Nike",
    "nike",
    "NIKE",
    "Puma",
    "puma",
    "PUMA",
    "Skechers",
    "Birkenstock",
    "Vans",
    "VANS",
    "New Balance",
    "FILA",
    "Li Ning",
    "Peak",
]


def _extract_brand(title: str) -> str:
    title_lower = title.lower()
    for brand in _KNOWN_BRANDS:
        if brand.lower() in title_lower:
            return brand.upper().replace(" ", "_")
    return "UNKNOWN"


def parse_rose_jsonl(file_path: Path) -> list[ProductRecord]:
    items = _parse_jsonl(file_path)
    records: list[ProductRecord] = []
    for item in items:
        ump_price = item.get("ump_price", item.get("show_price", 0))
        try:
            price = float(ump_price)
        except (ValueError, TypeError):
            price = 0.0
        title = item.get("title", "")
        records.append(
            ProductRecord(
                item_id=str(item.get("itemId", "")),
                title=title,
                price=price,
                shop=item.get("shop", ""),
                source="rose_10brands",
                brand=_extract_brand(title),
            )
        )
    return records
