"""Adaptive field mapping — pattern-based semantic column matching.

Resolution priority per column:
1. Sidecar .meta.yml (co-located with data file)
2. bi_cli.yml sources.*.metadata.fields (explicit per-source)
3. Global pattern matching (field_mapping.yml or defaults)
4. Auto-detection (numeric → avg metric)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PatternRule:
    pattern: str
    meaning: str
    unit: str = ""
    description: str = ""

    def matches(self, column_name: str) -> bool:
        return re.search(self.pattern, column_name, re.IGNORECASE) is not None


_DEFAULT_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        r"price|amount|cost|final.*price|calculated.*price"
        r"|原价|售价|均价|实付价|到手价",
        "price", "CNY",
    ),
    PatternRule(r"shop|store|seller|merchant|店铺|商店|卖家", "shop_name"),
    PatternRule(
        r"^(name|title)$|sku.*name|product.*name|item.*name"
        r"|商品名|产品名|标题|名称",
        "product_name",
    ),
    PatternRule(r"comment|review|content|text|评论|评价|内容", "comment_text"),
    PatternRule(
        r"time|date|timestamp|created|published|updated"
        r"|时间|日期|发布时间|采集时间",
        "timestamp",
    ),
    PatternRule(r"brand|manufacturer|品牌|厂家", "brand"),
    PatternRule(r"category|cat|type|class|分类|类别", "category"),
    PatternRule(r"user.*id|uid|customer.*id|用户.*id|评论人.*id", "user_id"),
    PatternRule(r"item.*id|sku.*id|product.*id|pid|商品.*id|编号", "item_id"),
    PatternRule(r"rating|score|star|grade|评分|打分|星级", "rating"),
    PatternRule(r"sales|volume|sold|quantity.*sold|销量|销售量|销售数", "sales_volume"),
    PatternRule(r"stock|inventory|quantity|available|库存|库存量", "stock"),
    PatternRule(r"sentiment|情感|情绪", "sentiment"),
)


@dataclass
class SourceError:
    source_id: str
    path: str
    error: str


class FieldMapper:
    """Pattern-based field meaning matcher."""

    def __init__(self, rules: tuple[PatternRule, ...] = _DEFAULT_RULES):
        self._rules = rules

    @classmethod
    def from_file(cls, path: Path) -> FieldMapper:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        rules = tuple(
            PatternRule(
                pattern=r["pattern"],
                meaning=r["meaning"],
                unit=r.get("unit", ""),
                description=r.get("description", ""),
            )
            for r in data.get("patterns", [])
        )
        return cls(rules if rules else _DEFAULT_RULES)

    @classmethod
    def default(cls) -> FieldMapper:
        return cls(_DEFAULT_RULES)

    def match(self, column_name: str) -> tuple[str, dict[str, Any]] | None:
        for rule in self._rules:
            if rule.matches(column_name):
                result: dict[str, Any] = {"meaning": rule.meaning}
                if rule.unit:
                    result["unit"] = rule.unit
                return rule.meaning, result
        return None

    def match_all(self, columns: list[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for col in columns:
            matched = self.match(col)
            if matched:
                result[col] = matched[1]
        return result
