from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from petfish_bi_cli.ingestion import ProductRecord


@dataclass
class RoseHtmlProduct:
    title: str
    item_id: str
    shop_name: str
    platform: str
    original_price: float
    final_price: float
    brand: str


def parse_rose_html(path: Path) -> list[RoseHtmlProduct]:
    html = Path(path).read_text(encoding="utf-8")
    cards = re.findall(
        r'<div class="card">(.*?)</div>\s*</div>\s*</div>\s*</div>\s*</div>', html, re.DOTALL
    )
    if not cards:
        cards = re.split(r'<div class="card">', html)[1:]

    products: list[RoseHtmlProduct] = []
    for card in cards:
        product = _parse_card(card)
        if product and product.original_price > 0:
            products.append(product)
    return products


def _parse_card(card: str) -> RoseHtmlProduct | None:
    title_m = re.search(r'class="product-title[^"]*"[^>]*>([^<]+)', card)
    if not title_m:
        return None
    title = title_m.group(1).strip()

    item_id_m = re.search(r"商品ID</span>\s*<span[^>]*>([^<]+)", card)
    item_id = item_id_m.group(1).strip() if item_id_m else ""

    shop_m = re.search(r"归属店铺</span>\s*.*?<span[^>]*>([^<]+)", card, re.DOTALL)
    shop_name = shop_m.group(1).strip() if shop_m else ""

    platform_m = re.search(r'class="platform-tag"[^>]*>([^<]+)', card)
    platform = platform_m.group(1).strip() if platform_m else ""

    original_price = _extract_price(card, "original-price")
    final_price = _extract_price(card, "current-price")
    if final_price == 0:
        final_price = original_price

    brand = _extract_brand(title)

    return RoseHtmlProduct(
        title=title,
        item_id=item_id,
        shop_name=shop_name,
        platform=platform,
        original_price=original_price,
        final_price=final_price,
        brand=brand,
    )


def _extract_price(card: str, price_class: str) -> float:
    pattern = rf'class="price-box\s+{price_class}"[^>]*>.*?class="price-value"[^>]*>￥([\d,.]+)'
    m = re.search(pattern, card, re.DOTALL)
    if m:
        return float(m.group(1).replace(",", ""))
    pattern2 = rf"{price_class}.*?￥([\d,.]+)"
    m2 = re.search(pattern2, card, re.DOTALL)
    if m2:
        return float(m2.group(1).replace(",", ""))
    return 0.0


_BRAND_PATTERNS = [
    "Hugo Boss",
    "HUGO BOSS",
    "BOSS",
    "Adidas",
    "ADIDAS",
    "Nike",
    "NIKE",
    "Anta",
    "安踏",
    "ANTA",
    "UGG",
    "Puma",
    "PUMA",
    "New Balance",
    "Skechers",
    "斯凯奇",
    "Crocs",
    "CROCS",
    "Li Ning",
    "李宁",
    "特步",
    "XTEP",
    "Converse",
    "Vans",
    "回力",
    "Warrior",
]


def _extract_brand(title: str) -> str:
    for brand in _BRAND_PATTERNS:
        if brand.lower() in title.lower():
            return brand
    first_word = title.split()[0] if title.split() else "Unknown"
    return first_word


def to_product_records(products: list[RoseHtmlProduct]) -> list[ProductRecord]:
    return [
        ProductRecord(
            sku_id=p.item_id,
            sku_name=p.title,
            price=p.final_price,
            shop_name=p.shop_name,
            platform=p.platform or "unknown",
            source="rose_html",
        )
        for p in products
    ]
