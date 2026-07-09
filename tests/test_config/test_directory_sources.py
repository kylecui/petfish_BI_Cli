"""Tests for directory-level metadata.yml sources."""
from __future__ import annotations

import json
from pathlib import Path

from petfish_bi_cli.config.source_registry import SourceRegistry


def _make_dir_source(
    tmp_path: Path, name: str, fmt: str, files: dict[str, str], meta: dict | None = None,
):
    d = tmp_path / name
    d.mkdir()
    for fname, content in files.items():
        (d / fname).write_text(content, encoding="utf-8")
    if meta is not None:
        import yaml

        (d / "metadata.yml").write_text(
            yaml.dump(meta, allow_unicode=True), encoding="utf-8",
        )
    return d


class TestDirectorySource:
    def test_directory_with_metadata_yml(self, tmp_path):
        _make_dir_source(
            tmp_path, "jd_products", "json",
            {"1.json": json.dumps({"items": [{"price": 100}]}),
             "2.json": json.dumps({"items": [{"price": 200}]})},
            {"type": "json", "description": "JD products",
             "fields": {"price": {"meaning": "price", "unit": "CNY"}}},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        assert "jd_products" in registry.all_sources()
        decl = registry.get("jd_products")
        assert decl is not None
        assert decl.type == "json"
        assert decl.description == "JD products"
        assert len(decl.data_files) == 2
        assert decl.find_field_by_meaning("price") == "price"

    def test_directory_no_metadata_skipped(self, tmp_path):
        d = tmp_path / "no_meta"
        d.mkdir()
        (d / "data.json").write_text(json.dumps({"items": [1]}))
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        assert "no_meta" not in registry.all_sources()

    def test_directory_source_data_files(self, tmp_path):
        _make_dir_source(
            tmp_path, "multi", "json",
            {"a.json": json.dumps([{"price": 1}]),
             "b.json": json.dumps([{"price": 2}]),
             "c.json": json.dumps([{"price": 3}])},
            {"type": "json"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        files = registry.resolve_data_files("multi")
        assert len(files) == 3

    def test_resolve_path_returns_first_file(self, tmp_path):
        _make_dir_source(
            tmp_path, "src", "json",
            {"1.json": json.dumps([{"price": 1}]),
             "2.json": json.dumps([{"price": 2}])},
            {"type": "json"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        path = registry.resolve_path("src")
        assert path is not None
        assert path.name == "1.json"

    def test_directory_auto_match_fields(self, tmp_path):
        _make_dir_source(
            tmp_path, "auto", "json",
            {"1.json": json.dumps({"items": [{"price": 100, "skuName": "A"}]})},
            {"type": "json"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("auto")
        assert decl is not None
        assert decl.find_field_by_meaning("price") == "price"
        assert decl.find_field_by_meaning("product_name") == "skuName"

    def test_directory_auto_infer_metrics(self, tmp_path):
        _make_dir_source(
            tmp_path, "metrics_test", "json",
            {"1.json": json.dumps({"items": [{"price": 100, "count": 5}]})},
            {"type": "json"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("metrics_test")
        assert decl is not None
        metric_names = [m.name for m in decl.metrics]
        assert "price" in metric_names

    def test_directory_and_standalone_coexist(self, tmp_path):
        _make_dir_source(
            tmp_path, "dir_source", "json",
            {"1.json": json.dumps([1])},
            {"type": "json"},
        )
        (tmp_path / "standalone.json").write_text(json.dumps([2]))
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        sources = registry.all_sources()
        assert "dir_source" in sources
        assert "standalone" in sources

    def test_directory_csv_source(self, tmp_path):
        _make_dir_source(
            tmp_path, "csv_source", "csv",
            {"jan.csv": "name,price\nA,100\nB,200\n",
             "feb.csv": "name,price\nC,300\n"},
            {"type": "csv", "description": "Monthly CSV data"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        decl = registry.get("csv_source")
        assert decl is not None
        assert decl.type == "csv"
        assert len(decl.data_files) == 2

    def test_empty_directory_with_metadata(self, tmp_path):
        d = tmp_path / "empty_dir"
        d.mkdir()
        import yaml

        (d / "metadata.yml").write_text(
            yaml.dump({"type": "json"}), encoding="utf-8",
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        assert "empty_dir" not in registry.all_sources()
        assert len(registry.errors) >= 1

    def test_directory_error_doesnt_break_others(self, tmp_path):
        bad = tmp_path / "bad_dir"
        bad.mkdir()
        import yaml

        (bad / "metadata.yml").write_text(
            yaml.dump({"type": "xml"}), encoding="utf-8",
        )
        _make_dir_source(
            tmp_path, "good_dir", "json",
            {"1.json": json.dumps([1])},
            {"type": "json"},
        )
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        assert "good_dir" in registry.all_sources()
        assert "bad_dir" not in registry.all_sources()
