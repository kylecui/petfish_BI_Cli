from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BIQuery:
    prompt: str
    data_sources: tuple = ()
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BIReport:
    answer: str
    data: dict = field(default_factory=dict)
    session_id: str = ""
    usage: dict = field(default_factory=dict)
    rich_content: str | None = None
    status: str = "ok"
