"""Data ingestion adapters for heterogeneous e-commerce data sources.

Each source has its own parser. There is no universal parser.
"""

from __future__ import annotations

from petfish_bi_cli.ingestion.crocs import CommentRecord, parse_crocs_csv
from petfish_bi_cli.ingestion.jd import ProductRecord, parse_jd_json
from petfish_bi_cli.ingestion.rose import parse_rose_jsonl
from petfish_bi_cli.ingestion.tmall import parse_tmall_jsonl

__all__ = [
    "parse_crocs_csv",
    "parse_jd_json",
    "parse_tmall_jsonl",
    "parse_rose_jsonl",
    "CommentRecord",
    "ProductRecord",
]
