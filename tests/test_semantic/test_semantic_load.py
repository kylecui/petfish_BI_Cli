from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.semantic import (
    load_all_metadata,
    load_entity_registry,
    load_source_metadata,
)

SEMANTIC_DIR = Path(__file__).parent.parent.parent / "references" / "semantic"


class TestEntitiesYml:
    def test_loads_without_error(self):
        reg = load_entity_registry(SEMANTIC_DIR)
        assert "entities" in reg
        names = [e["name"] for e in reg["entities"]]
        assert "brand" in names
        assert "platform" in names
        assert "metric" in names

    def test_brand_crocs_aliases(self):
        reg = load_entity_registry(SEMANTIC_DIR)
        brands = {e["name"]: e for e in reg["entities"]}
        crocs = brands["brand"]["values"]["CROCS"]
        assert "CROCS" in crocs
        assert "卡骆驰" in crocs


class TestCrocsXiaohongshuYml:
    def test_loads_correctly(self):
        meta = load_source_metadata(SEMANTIC_DIR / "crocs_xiaohongshu.yml")
        assert meta.source_id == "crocs_xiaohongshu"
        assert meta.source_type == "csv"
        assert "评论内容" in [c["name"] for c in meta.columns]

    def test_has_comment_metrics(self):
        meta = load_source_metadata(SEMANTIC_DIR / "crocs_xiaohongshu.yml")
        metric_names = [m["name"] for m in meta.metrics]
        assert "comment_count" in metric_names


class TestJdProductsYml:
    def test_loads_correctly(self):
        meta = load_source_metadata(SEMANTIC_DIR / "jd_products.yml")
        assert meta.source_id == "jd_products"
        assert meta.source_type == "json"
        assert meta.json_path == "raw_data.search_results[]"

    def test_json_path_in_schema(self):
        yml_path = SEMANTIC_DIR / "jd_products.yml"
        import yaml

        with open(yml_path) as f:
            data = yaml.safe_load(f)
        assert data["schema"]["json_path"] == "raw_data.search_results[]"

    def test_has_price_metrics(self):
        meta = load_source_metadata(SEMANTIC_DIR / "jd_products.yml")
        metric_names = [m["name"] for m in meta.metrics]
        assert "avg_price" in metric_names
        assert "min_price" in metric_names


class TestTmallProductsYml:
    def test_loads_correctly(self):
        meta = load_source_metadata(SEMANTIC_DIR / "tmall_products.yml")
        assert meta.source_id == "tmall_products"
        assert meta.source_type == "jsonl"
        assert meta.items_path == "extracted_items[]"

    def test_has_shop_count_metric(self):
        meta = load_source_metadata(SEMANTIC_DIR / "tmall_products.yml")
        metric_names = [m["name"] for m in meta.metrics]
        assert "shop_count" in metric_names


class TestRose10brandsYml:
    def test_loads_correctly(self):
        meta = load_source_metadata(SEMANTIC_DIR / "rose_10brands.yml")
        assert meta.source_id == "rose_10brands"
        assert meta.source_type == "jsonl"
        assert "ump_price" in [c["name"] for c in meta.columns]

    def test_has_known_brand_values(self):
        meta = load_source_metadata(SEMANTIC_DIR / "rose_10brands.yml")
        brand_entity = [e for e in meta.entities if e["name"] == "brand"][0]
        known = brand_entity.get("known_values", [])
        assert "CROCS" in known
        assert "Adidas" in known


class TestLoadAllMetadata:
    def test_returns_four_sources(self):
        all_meta = load_all_metadata(SEMANTIC_DIR)
        assert len(all_meta) == 4
        assert "crocs_xiaohongshu" in all_meta
        assert "jd_products" in all_meta
        assert "tmall_products" in all_meta
        assert "rose_10brands" in all_meta
