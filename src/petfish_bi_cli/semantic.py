from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    source_type: str
    file_pattern: str
    description: str
    columns: tuple = ()
    metrics: tuple = ()
    entities: tuple = ()
    example_questions: tuple = ()
    json_path: str = ""
    items_path: str = ""


def load_source_metadata(yaml_path: Path) -> SourceMetadata:
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    schema = data.get("schema", {})
    json_path = schema.get("json_path", "")
    items_path = ""
    columns = tuple(schema.get("columns", []))
    if "item_columns" in schema:
        columns = tuple(schema["item_columns"])
    if "jsonl_structure" in schema:
        items_path = schema["jsonl_structure"].get("items_path", "")
        columns = tuple(schema["jsonl_structure"].get("item_columns", columns))

    return SourceMetadata(
        source_id=data["source_id"],
        source_type=data["source_type"],
        file_pattern=data.get("file_pattern", ""),
        description=data.get("description", ""),
        columns=columns,
        metrics=tuple(data.get("metrics", [])),
        entities=tuple(data.get("entities", [])),
        example_questions=tuple(data.get("example_questions", [])),
        json_path=json_path,
        items_path=items_path,
    )


def load_all_metadata(semantic_dir: Path) -> dict[str, SourceMetadata]:
    result: dict[str, SourceMetadata] = {}
    for yml in sorted(semantic_dir.glob("*.yml")):
        if yml.name == "entities.yml":
            continue
        meta = load_source_metadata(yml)
        result[meta.source_id] = meta
    return result


def load_entity_registry(semantic_dir: Path) -> dict:
    entities_path = semantic_dir / "entities.yml"
    if not entities_path.exists():
        return {}
    with open(entities_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
