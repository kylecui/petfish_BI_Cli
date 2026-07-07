from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommentRecord:
    search_keyword: str
    note_title: str
    blogger: str
    comment_text: str
    comment_time: str
    is_recent: bool


def parse_crocs_csv(file_path: Path) -> list[CommentRecord]:
    records: list[CommentRecord] = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment = row.get("评论内容", "")
            if comment in ("无", "", None):
                continue
            records.append(
                CommentRecord(
                    search_keyword=row.get("搜索关键词", ""),
                    note_title=row.get("笔记标题", ""),
                    blogger=row.get("博主名", ""),
                    comment_text=comment,
                    comment_time=row.get("评论时间", ""),
                    is_recent=row.get("是否近3天新增", "否") == "是",
                )
            )
    return records
