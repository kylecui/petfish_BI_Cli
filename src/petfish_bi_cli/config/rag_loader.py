from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from petfishframework.core.contracts import Retriever
from petfishframework.retrieval import CRAGRetriever

from petfish_bi_cli.retrieval.chinese_retriever import ChineseRetriever


def build_retriever(config: dict[str, Any]) -> Retriever | None:
    """Build a CRAGRetriever from retrieval config.

    Config format:
        retrievers:
          crocs_comments:
            type: crag
            source: crocs_xiaohongshu
            index:
              field: 评论内容
            retrieval:
              top_k: 5
    """
    retrievers_cfg = config.get("retrievers", {})
    if not retrievers_cfg:
        return None

    base = ChineseRetriever()

    for _name, cfg in retrievers_cfg.items():
        if "documents" in cfg:
            for doc in cfg["documents"]:
                base.add(doc["content"], metadata=doc.get("metadata", {}))
        else:
            _populate_retriever(base, cfg)

    if base.doc_count == 0:
        return None

    return CRAGRetriever(base_retriever=base)


def _populate_retriever(base: ChineseRetriever, cfg: dict[str, Any]) -> None:
    source = cfg.get("source", "")
    index_field = cfg.get("index", {}).get("field", "")

    docs = _load_source_documents(source, index_field)
    for doc_text, metadata in docs:
        base.add(doc_text, metadata={"source": source, **metadata})


def _load_source_documents(source: str, field: str) -> list[tuple[str, dict]]:
    """Load documents from data source into (text, metadata) pairs."""
    data_root = Path("references")

    if source == "crocs_xiaohongshu":
        return _load_crocs_comments(data_root, field)
    elif source == "tmall_products":
        return _load_tmall_titles(data_root, field)
    elif source == "jd_products":
        return _load_jd_titles(data_root, field)
    return []


def _load_crocs_comments(data_root: Path, field: str) -> list[tuple[str, dict]]:
    from petfish_bi_cli.ingestion.crocs import parse_crocs_csv

    csv_path = data_root / "CROCS_原始数据_20260605_144849.csv"
    if not csv_path.exists():
        return []

    records = parse_crocs_csv(csv_path)
    docs: list[tuple[str, dict]] = []
    for r in records:
        text = r.comment_text if field in ("评论内容", "") else getattr(r, field, r.comment_text)
        if text and len(text) > 5:
            docs.append((text, {"note_title": r.note_title, "comment_time": r.comment_time}))
    return docs


def _load_tmall_titles(data_root: Path, field: str) -> list[tuple[str, dict]]:
    from petfish_bi_cli.ingestion.tmall import parse_tmall_jsonl

    jsonl_path = data_root / "TMALL_CROCS_Raw_Memory_Dump.json"
    if not jsonl_path.exists():
        return []

    records = parse_tmall_jsonl(jsonl_path)
    docs: list[tuple[str, dict]] = []
    for r in records:
        text = r.title
        if text and len(text) > 2:
            docs.append((text, {"shop": r.shop, "price": r.price}))
    return docs[:200]


def _load_jd_titles(data_root: Path, field: str) -> list[tuple[str, dict]]:
    from petfish_bi_cli.ingestion.jd import parse_jd_json

    json_path = data_root / "JD_CROCS_Raw_Memory_Dump.json"
    if not json_path.exists():
        return []

    records = parse_jd_json(json_path)
    docs: list[tuple[str, dict]] = []
    for r in records:
        text = r.sku_name
        if text and len(text) > 2:
            docs.append((text, {"shop": r.shop_name, "price": r.price}))
    return docs


def load_retrieval_config(config_path: str | Path = "configs/bi_cli.yml") -> dict[str, Any]:
    """Load just the retrieval section from bi_cli.yml."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("retrieval", {})
