"""Tests for field metadata — semantic column declarations."""
from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.config.source_registry import SourceRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"

_CONFIG_WITH_FIELDS = {
    "sources": {
        "jd_products": {
            "path": "mock_jd_products.json",
            "metadata": {
                "fields": {
                    "calculatedFinalPrice": {
                        "meaning": "price",
                        "unit": "CNY",
                        "aliases": ["均价", "实付价"],
                        "description": "考虑优惠券后的实付价格",
                    },
                    "skuName": {
                        "meaning": "product_name",
                        "aliases": ["title"],
                    },
                    "shopName": {
                        "meaning": "shop_name",
                    },
                    "isJdSelf": {
                        "meaning": "is_self_operated",
                        "mapping": {"true": "京东自营", "false": "第三方"},
                    },
                },
            },
        },
    },
}


class TestFieldMetadataParsing:
    def test_fields_parsed_from_config(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert "calculatedFinalPrice" in decl.fields
        assert "skuName" in decl.fields

    def test_field_meaning(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        price_field = decl.fields["calculatedFinalPrice"]
        assert price_field.meaning == "price"
        assert price_field.unit == "CNY"

    def test_field_aliases(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert "均价" in decl.fields["calculatedFinalPrice"].aliases

    def test_field_mapping(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        mapping = decl.fields["isJdSelf"].mapping
        assert mapping.get("true") == "京东自营"


class TestFindFieldByMeaning:
    def test_find_price_column(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "calculatedFinalPrice"

    def test_find_product_name(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_meaning("product_name") == "skuName"

    def test_find_nonexistent_meaning(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_meaning("comment_text") is None


class TestFindFieldByAlias:
    def test_find_by_chinese_alias(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_alias("均价") == "calculatedFinalPrice"

    def test_find_by_english_alias(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_alias("title") == "skuName"

    def test_find_nonexistent_alias(self):
        registry = SourceRegistry(config=_CONFIG_WITH_FIELDS, data_root=DATA_ROOT)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.find_field_by_alias("nonexistent") is None


class TestNoMetadata:
    def test_auto_match_fills_fields(self):
        config = {"sources": {"test": {"path": "mock_jd_products.json"}}}
        registry = SourceRegistry(config=config, data_root=DATA_ROOT)
        decl = registry.get("test")
        assert decl is not None
        assert len(decl.fields) > 0
        assert decl.find_field_by_meaning("price") is not None

    def test_no_fields_when_columns_dont_match(self, tmp_path):
        import json

        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps({"items": [{"xyz_field": 100}]}))
        config = {"sources": {"test": {"path": "test.json"}}}
        registry = SourceRegistry(config=config, data_root=tmp_path)
        decl = registry.get("test")
        assert decl is not None
        assert len(decl.fields) == 0
        assert decl.find_field_by_meaning("price") is None
