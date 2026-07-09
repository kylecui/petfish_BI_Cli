"""Tests for FieldMapper + sidecar metadata + error handling + auto-match."""
from __future__ import annotations

import json
from pathlib import Path

from petfish_bi_cli.config.field_mapping import FieldMapper, PatternRule, SourceError
from petfish_bi_cli.config.source_registry import SourceRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestFieldMapper:
    def test_match_price_column(self):
        mapper = FieldMapper.default()
        result = mapper.match("calculatedFinalPrice")
        assert result is not None
        assert result[0] == "price"

    def test_match_chinese_price(self):
        mapper = FieldMapper.default()
        result = mapper.match("实付价")
        assert result is not None
        assert result[0] == "price"

    def test_match_product_name(self):
        mapper = FieldMapper.default()
        result = mapper.match("skuName")
        assert result is not None
        assert result[0] == "product_name"

    def test_match_comment_text(self):
        mapper = FieldMapper.default()
        result = mapper.match("评论内容")
        assert result is not None
        assert result[0] == "comment_text"

    def test_no_match(self):
        mapper = FieldMapper.default()
        assert mapper.match("random_field_xyz") is None

    def test_match_all(self):
        mapper = FieldMapper.default()
        result = mapper.match_all(["price", "title", "shopName", "random"])
        assert "price" in result
        assert "title" in result
        assert "shopName" in result
        assert "random" not in result

    def test_from_file(self, tmp_path):
        mapping_file = tmp_path / "field_mapping.yml"
        mapping_file.write_text(
            "patterns:\n"
            "  - pattern: '.*foo.*'\n"
            "    meaning: custom_meaning\n"
        )
        mapper = FieldMapper.from_file(mapping_file)
        result = mapper.match("foo_bar")
        assert result is not None
        assert result[0] == "custom_meaning"

    def test_custom_rules(self):
        rule = PatternRule(pattern=r"^\d+$", meaning="numeric_id")
        mapper = FieldMapper(rules=(rule,))
        result = mapper.match("123")
        assert result is not None
        assert result[0] == "numeric_id"
        assert mapper.match("abc") is None


class TestSidecarMetadata:
    def test_sidecar_yml_loaded(self, tmp_path):
        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps({"items": [{"price": 100, "name": "A"}]}))
        sidecar = tmp_path / "test.meta.yml"
        sidecar.write_text(
            "fields:\n"
            "  price:\n"
            "    meaning: price\n"
            "    unit: CNY\n"
            "  name:\n"
            "    meaning: product_name\n"
        )
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("test")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"
        assert decl.find_field_by_meaning("product_name") == "name"

    def test_no_sidecar_uses_auto_match(self, tmp_path):
        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps({"items": [{"price": 100, "shopName": "Store"}]}))
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("test")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"
        assert decl.find_field_by_meaning("shop_name") == "shopName"

    def test_sidecar_yaml_extension(self, tmp_path):
        data_file = tmp_path / "test.csv"
        data_file.write_text("price,name\n100,A\n")
        sidecar = tmp_path / "test.meta.yaml"
        sidecar.write_text(
            "fields:\n"
            "  price:\n"
            "    meaning: price\n"
        )
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("test")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"


class TestErrorHandling:
    def test_corrupted_json_skipped(self, tmp_path):
        good = tmp_path / "good.json"
        good.write_text(json.dumps({"items": [{"price": 100}]}))
        bad = tmp_path / "bad.json"
        bad.write_text("{broken json content")
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        assert "good" in registry.all_sources()
        assert len(registry.errors) > 0

    def test_errors_accessible(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{broken")
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        assert len(registry.errors) >= 1
        assert isinstance(registry.errors[0], SourceError)

    def test_one_bad_source_doesnt_break_others(self, tmp_path):
        for i in range(5):
            (tmp_path / f"src_{i}.json").write_text(
                json.dumps({"items": [{"price": i}]})
            )
        (tmp_path / "broken.json").write_text("not json at all")
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        sources = registry.all_sources()
        assert len(sources) == 5
        assert "broken" not in sources

    def test_config_source_missing_file_graceful(self, tmp_path):
        config = {
            "sources": {
                "bad": {"path": "nonexistent.json"},
            }
        }
        registry = SourceRegistry(config=config, data_root=tmp_path)
        assert "bad" in registry.all_sources()
        assert registry.resolve_path("bad") is None


class TestResolutionPriority:
    def test_config_metadata_overrides_sidecar(self, tmp_path):
        data_file = tmp_path / "test.json"
        data_file.write_text(json.dumps({"items": [{"price": 100}]}))
        sidecar = tmp_path / "test.meta.yml"
        sidecar.write_text("fields:\n  price:\n    meaning: rating\n")
        config = {
            "sources": {
                "test": {
                    "path": "test.json",
                    "metadata": {
                        "fields": {
                            "price": {"meaning": "price"},
                        },
                    },
                }
            }
        }
        registry = SourceRegistry(config=config, data_root=tmp_path)
        decl = registry.get("test")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"
        assert decl.find_field_by_meaning("rating") is None

    def test_auto_match_fills_gaps(self, tmp_path):
        data_file = tmp_path / "test.json"
        data_file.write_text(
            json.dumps({"items": [{"price": 100, "skuName": "A", "random": "x"}]})
        )
        registry = SourceRegistry(
            config={},
            data_root=tmp_path,
            semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("test")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"
        assert decl.find_field_by_meaning("product_name") == "skuName"
