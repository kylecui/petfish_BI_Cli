"""SourceRegistry — config-driven data source declarations.

Replaces the file-based semantic/*.yml loading with config-section-driven
source declarations. Falls back to semantic/*.yml when no `sources:` section
is present in bi_cli.yml (backward compat).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from petfish_bi_cli.semantic import SourceMetadata, load_all_metadata

_VALID_TYPES = frozenset({"json", "csv", "jsonl"})


@dataclass(frozen=True)
class MetricSpec:
    name: str
    column: str = ""
    aggregation: str = "count"
    unit: str = ""
    aliases: tuple[str, ...] = ()
    compute: str = ""


@dataclass(frozen=True)
class EntitySpec:
    name: str
    values: tuple[str, ...] = ()
    source_column: str = ""
    extractable_from: str = ""
    mapping: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceDeclaration:
    source_id: str
    type: str
    path: Path
    description: str
    schema: dict[str, Any] = field(default_factory=dict)
    metrics: tuple[MetricSpec, ...] = ()
    entities: tuple[EntitySpec, ...] = ()
    example_questions: tuple[str, ...] = ()
    file_pattern: str = ""


class SourceRegistry:
    """Loads source declarations from config; falls back to semantic/*.yml."""

    def __init__(
        self,
        config: dict[str, Any],
        data_root: Path | None = None,
        semantic_dir: Path | None = None,
    ):
        self._data_root = data_root or Path("references")
        self._semantic_dir = semantic_dir or self._data_root / "semantic"
        self._sources: dict[str, SourceDeclaration] = {}

        sources_config = config.get("sources")
        if sources_config:
            for source_id, spec in sources_config.items():
                self._sources[source_id] = self._parse_source(source_id, spec)
        else:
            self._sources = self._load_from_semantic_dir()

    def get(self, source_id: str) -> SourceDeclaration | None:
        return self._sources.get(source_id)

    def all_sources(self) -> dict[str, SourceDeclaration]:
        return dict(self._sources)

    def to_metadata(self) -> dict[str, SourceMetadata]:
        """Convert declarations to legacy SourceMetadata for backward compat."""
        result: dict[str, SourceMetadata] = {}
        for source_id, decl in self._sources.items():
            result[source_id] = self._decl_to_metadata(decl)
        return result

    # --- internals ---

    def _parse_source(self, source_id: str, spec: dict) -> SourceDeclaration:
        source_type = spec.get("type", "json")
        if source_type not in _VALID_TYPES:
            raise ValueError(
                f"Unknown source type '{source_type}' for source '{source_id}'. "
                f"Valid types: {', '.join(sorted(_VALID_TYPES))}"
            )

        rel_path = Path(spec["path"]) if "path" in spec else Path("")
        resolved_path = self._data_root / rel_path if not rel_path.is_absolute() else rel_path

        metrics = tuple(
            MetricSpec(
                name=m["name"],
                column=m.get("column", m.get("source_column", "")),
                aggregation=m.get("aggregation", "count"),
                unit=m.get("unit", ""),
                aliases=tuple(m.get("aliases", [])),
                compute=m.get("compute", ""),
            )
            for m in spec.get("metrics", [])
        )

        entities = tuple(
            EntitySpec(
                name=e["name"],
                values=tuple(e.get("values", [])),
                source_column=e.get("source_column", ""),
                extractable_from=e.get("extractable_from", ""),
                mapping=dict(e.get("mapping", {})),
            )
            for e in spec.get("entities", [])
        )

        return SourceDeclaration(
            source_id=source_id,
            type=source_type,
            path=resolved_path,
            description=spec.get("description", ""),
            schema=spec.get("schema", {}),
            metrics=metrics,
            entities=entities,
            example_questions=tuple(spec.get("example_questions", [])),
            file_pattern=spec.get("file_pattern", spec.get("path", "")),
        )

    def _load_from_semantic_dir(self) -> dict[str, SourceDeclaration]:
        """Fallback: load from semantic/*.yml using legacy loader."""
        meta_dict = load_all_metadata(self._semantic_dir)
        result: dict[str, SourceDeclaration] = {}
        for source_id, meta in meta_dict.items():
            result[source_id] = self._metadata_to_decl(source_id, meta)
        return result

    def _metadata_to_decl(self, source_id: str, meta: SourceMetadata) -> SourceDeclaration:
        return SourceDeclaration(
            source_id=source_id,
            type=meta.source_type,
            path=self._data_root / meta.file_pattern if meta.file_pattern else self._data_root,
            description=meta.description,
            schema={"json_path": meta.json_path} if meta.json_path else {},
            metrics=tuple(
                MetricSpec(
                    name=m.get("name", ""),
                    column=m.get("source_column", m.get("column", "")),
                    aggregation=m.get("aggregation", "count"),
                    unit=m.get("unit", ""),
                    aliases=tuple(m.get("aliases", [])),
                    compute=m.get("compute", ""),
                )
                for m in meta.metrics
            ),
            entities=tuple(
                EntitySpec(
                    name=e.get("name", ""),
                    values=tuple(e.get("values", [])),
                    source_column=e.get("source_column", ""),
                    extractable_from=e.get("extractable_from", ""),
                    mapping=dict(e.get("mapping", {})),
                )
                for e in meta.entities
            ),
            example_questions=meta.example_questions,
            file_pattern=meta.file_pattern,
        )

    @staticmethod
    def _decl_to_metadata(decl: SourceDeclaration) -> SourceMetadata:
        metrics_list = [
            {
                "name": m.name,
                "source_column": m.column,
                "aggregation": m.aggregation,
                "unit": m.unit,
                "aliases": list(m.aliases),
                "compute": m.compute,
            }
            for m in decl.metrics
        ]
        entities_list = [
            {
                "name": e.name,
                "values": list(e.values),
                "source_column": e.source_column,
                "extractable_from": e.extractable_from,
                "mapping": e.mapping,
            }
            for e in decl.entities
        ]
        return SourceMetadata(
            source_id=decl.source_id,
            source_type=decl.type,
            file_pattern=decl.file_pattern,
            description=decl.description,
            columns=(),
            metrics=tuple(metrics_list),
            entities=tuple(entities_list),
            example_questions=decl.example_questions,
            json_path=decl.schema.get("json_path", ""),
            items_path=decl.schema.get("items_path", ""),
        )
