"""Tests for auto-detection: format detection + metric inference + directory scan."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from petfish_bi_cli.config.auto_detect import detect_format, infer_metrics
from petfish_bi_cli.config.source_registry import SourceRegistry

DATA_ROOT = Path(__file__).parent.parent.parent / "references"


class TestDetectFormat:
    def test_detect_json(self):
        assert detect_format(DATA_ROOT / "mock_jd_products.json") == "json"

    def test_detect_csv(self):
        assert detect_format(DATA_ROOT / "mock_crocs_xiaohongshu.csv") == "csv"

    def test_detect_jsonl_single_line(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"key": "val"}))
        assert detect_format(f) == "json"

    def test_detect_jsonl_multi_line(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}\n{"b": 2}\n')
        assert detect_format(f) == "jsonl"

    def test_detect_csv_by_content(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("name,age\nAlice,30\nBob,25\n")
        assert detect_format(f) == "csv"

    def test_unknown_format_raises(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        with pytest.raises(ValueError, match="Cannot detect"):
            detect_format(f)


class TestInferMetrics:
    def test_csv_numeric_columns(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("name,price,count\nA,100,5\nB,200,3\nC,150,8\n")
        metrics = infer_metrics(f, "csv")
        names = [m["name"] for m in metrics]
        assert "price" in names
        assert "count" in names
        assert "name" not in names

    def test_csv_no_numeric_columns(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("name,color\nA,red\nB,blue\n")
        metrics = infer_metrics(f, "csv")
        assert len(metrics) == 1
        assert metrics[0]["aggregation"] == "count"

    def test_json_numeric_fields(self):
        metrics = infer_metrics(DATA_ROOT / "mock_jd_products.json", "json")
        names = [m["name"] for m in metrics]
        assert "calculatedFinalPrice" in names or "originalPrice" in names

    def test_jsonl_numeric_fields(self):
        metrics = infer_metrics(DATA_ROOT / "mock_tmall_products.json", "jsonl")
        assert len(metrics) > 0

    def test_empty_file_returns_count(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("{}")
        metrics = infer_metrics(f, "json")
        assert len(metrics) >= 1


class TestDirectoryScan:
    def test_scans_data_root(self):
        registry = SourceRegistry(
            config={}, data_root=DATA_ROOT, semantic_dir=DATA_ROOT / "nonexistent",
        )
        sources = registry.all_sources()
        assert "mock_jd_products" in sources
        assert "mock_crocs_xiaohongshu" in sources

    def test_auto_detected_type(self):
        registry = SourceRegistry(
            config={}, data_root=DATA_ROOT, semantic_dir=DATA_ROOT / "nonexistent",
        )
        decl = registry.get("mock_crocs_xiaohongshu")
        assert decl is not None
        assert decl.type == "csv"

    def test_auto_detected_metrics(self):
        registry = SourceRegistry(
            config={}, data_root=DATA_ROOT, semantic_dir=DATA_ROOT / "nonexistent",
        )
        decl = registry.get("mock_jd_products")
        assert decl is not None
        assert len(decl.metrics) > 0

    def test_empty_directory(self, tmp_path):
        registry = SourceRegistry(
            config={}, data_root=tmp_path, semantic_dir=tmp_path / "nonexistent",
        )
        assert len(registry.all_sources()) == 0

    def test_sources_config_overrides_scan(self):
        config = {"sources": {"custom": {"path": "mock_jd_products.json"}}}
        registry = SourceRegistry(config=config, data_root=DATA_ROOT)
        assert "custom" in registry.all_sources()
        assert "mock_tmall_products" not in registry.all_sources()


class TestTypeOptionalInConfig:
    def test_type_omitted_auto_detected(self):
        config = {"sources": {"test": {"path": "mock_crocs_xiaohongshu.csv"}}}
        registry = SourceRegistry(config=config, data_root=DATA_ROOT)
        decl = registry.get("test")
        assert decl is not None
        assert decl.type == "csv"

    def test_type_explicit_still_works(self):
        config = {"sources": {"test": {"type": "json", "path": "mock_jd_products.json"}}}
        registry = SourceRegistry(config=config, data_root=DATA_ROOT)
        decl = registry.get("test")
        assert decl is not None
        assert decl.type == "json"

    def test_metrics_omitted_auto_inferred(self):
        config = {"sources": {"test": {"path": "mock_jd_products.json"}}}
        registry = SourceRegistry(config=config, data_root=DATA_ROOT)
        decl = registry.get("test")
        assert decl is not None
        assert len(decl.metrics) > 0
