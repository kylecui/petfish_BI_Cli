"""Tests for SourceRegistry — config-driven data source declarations."""
from __future__ import annotations

import pytest

from petfish_bi_cli.config.source_registry import (
    EntitySpec,
    MetricSpec,
    SourceRegistry,
)
from petfish_bi_cli.semantic import SourceMetadata

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CONFIG_WITH_SOURCES = {
    "sources": {
        "jd_products": {
            "type": "json",
            "path": "mock_jd_products.json",
            "description": "京东商品列表",
            "schema": {
                "json_path": "raw_data.search_results[]",
            },
            "metrics": [
                {
                    "name": "avg_price",
                    "column": "calculatedFinalPrice",
                    "aggregation": "avg",
                    "unit": "CNY",
                    "aliases": ["均价"],
                },
                {
                    "name": "product_count",
                    "aggregation": "count",
                },
            ],
            "entities": [
                {
                    "name": "brand",
                    "values": ["CROCS"],
                    "source_column": "skuName",
                },
            ],
        },
        "tmall_products": {
            "type": "json",
            "path": "tmall/tmall_crocs_raw.json",
            "description": "天猫CROCS商品",
        },
    },
}

SAMPLE_CONFIG_NO_SOURCES = {
    "model": {"provider": "fake"},
}


# ---------------------------------------------------------------------------
# SourceDeclaration parsing
# ---------------------------------------------------------------------------

class TestSourceRegistryParsing:
    def test_parses_sources_from_config_dict(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        assert len(registry.all_sources()) == 2

    def test_source_has_correct_id(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        assert "jd_products" in registry.all_sources()
        assert "tmall_products" in registry.all_sources()

    def test_source_declaration_fields(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.source_id == "jd_products"
        assert decl.type == "json"
        assert decl.description == "京东商品列表"
        assert decl.path == data_root / "mock_jd_products.json"

    def test_metrics_parsed_correctly(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        decl = registry.get("jd_products")
        assert len(decl.metrics) == 2
        avg_price = decl.metrics[0]
        assert avg_price.name == "avg_price"
        assert avg_price.column == "calculatedFinalPrice"
        assert avg_price.aggregation == "avg"
        assert avg_price.unit == "CNY"
        assert "均价" in avg_price.aliases

    def test_entities_parsed_correctly(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        decl = registry.get("jd_products")
        assert len(decl.entities) == 1
        assert decl.entities[0].name == "brand"
        assert "CROCS" in decl.entities[0].values

    def test_source_without_metrics_has_empty_tuple(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        decl = registry.get("tmall_products")
        assert decl.metrics == ()

    def test_get_nonexistent_returns_none(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        assert registry.get("nonexistent") is None

    def test_invalid_source_type_raises(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        bad_config = {
            "sources": {
                "bad": {"type": "xml", "path": "bad.xml"},
            }
        }
        registry = SourceRegistry(config=bad_config, data_root=data_root)
        assert "bad" not in registry.all_sources()
        assert any("Unknown source type" in e.error for e in registry.errors)


# ---------------------------------------------------------------------------
# Backward compat: semantic dir fallback
# ---------------------------------------------------------------------------

class TestSourceRegistryFallback:
    def test_falls_back_to_semantic_dir_when_no_sources(self, tmp_path):
        semantic_dir = tmp_path / "semantic"
        semantic_dir.mkdir()
        # Create a minimal semantic YAML
        (semantic_dir / "test_source.yml").write_text(
            'source_id: test_source\n'
            'source_type: csv\n'
            'description: "Test source"\n'
            'file_pattern: "test.csv"\n',
            encoding="utf-8",
        )
        registry = SourceRegistry(
            config=SAMPLE_CONFIG_NO_SOURCES,
            data_root=tmp_path,
            semantic_dir=semantic_dir,
        )
        assert len(registry.all_sources()) >= 1
        assert "test_source" in registry.all_sources()

    def test_empty_config_uses_semantic_fallback(self, tmp_path):
        semantic_dir = tmp_path / "semantic"
        semantic_dir.mkdir()
        (semantic_dir / "a.yml").write_text(
            'source_id: a\nsource_type: csv\ndescription: "A"\nfile_pattern: "a.csv"\n',
            encoding="utf-8",
        )
        registry = SourceRegistry(config={}, data_root=tmp_path, semantic_dir=semantic_dir)
        assert "a" in registry.all_sources()


# ---------------------------------------------------------------------------
# to_metadata: backward compat conversion
# ---------------------------------------------------------------------------

class TestSourceRegistryToMetadata:
    def test_to_metadata_returns_source_metadata_dict(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        metadata = registry.to_metadata()
        assert "jd_products" in metadata
        meta = metadata["jd_products"]
        assert isinstance(meta, SourceMetadata)
        assert meta.source_id == "jd_products"
        assert meta.source_type == "json"
        assert meta.description == "京东商品列表"

    def test_to_metadata_preserves_metrics(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        meta = registry.to_metadata()["jd_products"]
        assert len(meta.metrics) == 2
        metric_names = [m["name"] for m in meta.metrics]
        assert "avg_price" in metric_names
        assert "product_count" in metric_names

    def test_to_metadata_preserves_json_path(self, tmp_path):
        data_root = tmp_path / "data"
        data_root.mkdir()
        registry = SourceRegistry(config=SAMPLE_CONFIG_WITH_SOURCES, data_root=data_root)
        meta = registry.to_metadata()["jd_products"]
        assert meta.json_path == "raw_data.search_results[]"


# ---------------------------------------------------------------------------
# MetricSpec and EntitySpec
# ---------------------------------------------------------------------------

class TestMetricSpec:
    def test_defaults(self):
        m = MetricSpec(name="count")
        assert m.aggregation == "count"
        assert m.column == ""
        assert m.unit == ""

    def test_compute_field(self):
        m = MetricSpec(name="discount", compute="a - b")
        assert m.compute == "a - b"


class TestEntitySpec:
    def test_defaults(self):
        e = EntitySpec(name="brand")
        assert e.values == ()
        assert e.source_column == ""
