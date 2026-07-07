from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductRecord:
    item_id: str
    title: str
    price: float
    shop: str
    source: str = ""
    brand: str = ""


def parse_jd_json(file_path: Path) -> list[ProductRecord]:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("raw_data", {}).get("search_results", [])
    records: list[ProductRecord] = []
    for item in results:
        price = item.get("calculatedFinalPrice", 0.0)
        records.append(
            ProductRecord(
                item_id=str(item.get("skuId", "")),
                title=item.get("skuName", ""),
                price=float(price) if price else 0.0,
                shop=item.get("shopName", ""),
                source="jd_products",
            )
        )
    return records
