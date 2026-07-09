"""SourceRegistry — config-driven data source declarations.

Three resolution levels:
1. Explicit sources in config (type optional — auto-detected if omitted)
2. Directory scan: no sources → auto-discover files in data.root
3. Semantic YAML fallback: legacy references/semantic/*.yml
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from petfish_bi_cli.config.auto_detect import detect_format, infer_metrics
from petfish_bi_cli.config.field_mapping import FieldMapper, SourceError
from petfish_bi_cli.semantic import SourceMetadata, load_all_metadata

_VALID_TYPES = frozenset({"json", "csv", "jsonl"})
_DATA_EXTENSIONS = frozenset({".json", ".csv", ".jsonl"})

_SEMANTIC_MEANINGS = frozenset({
    "price", "product_name", "shop_name", "comment_text",
    "timestamp", "brand", "category", "user_id", "item_id",
    "sentiment", "rating", "sales_volume", "stock",
})


@dataclass(frozen=True)
class FieldMetadata:
    column: str
    meaning: str = ""
    unit: str = ""
    aliases: tuple[str, ...] = ()
    mapping: dict[str, str] = field(default_factory=dict)
    description: str = ""


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
    fields: dict[str, FieldMetadata] = field(default_factory=dict)
    example_questions: tuple[str, ...] = ()
    file_pattern: str = ""
    data_files: tuple[Path, ...] = ()

    def find_field_by_meaning(self, meaning: str) -> str | None:
        for column, meta in self.fields.items():
            if meta.meaning == meaning:
                return column
        return None

    def find_field_by_alias(self, alias: str) -> str | None:
        alias_lower = alias.lower()
        for column, meta in self.fields.items():
            if alias_lower in [a.lower() for a in meta.aliases]:
                return column
            if alias_lower == column.lower():
                return column
        return None


class SourceRegistry:
    """Loads source declarations from config; falls back to semantic/*.yml."""

    def __init__(
        self,
        config: dict[str, Any],
        data_root: Path | None = None,
        semantic_dir: Path | None = None,
        field_mapper: FieldMapper | None = None,
    ):
        self._data_root = data_root or Path("references")
        self._semantic_dir = semantic_dir or self._data_root / "semantic"
        self._field_mapper = field_mapper or FieldMapper.default()
        self._sources: dict[str, SourceDeclaration] = {}
        self._errors: list[SourceError] = []

        sources_config = config.get("sources")
        if sources_config:
            for source_id, spec in sources_config.items():
                try:
                    self._sources[source_id] = self._parse_source(source_id, spec)
                except Exception as exc:
                    self._errors.append(
                        SourceError(source_id, str(spec.get("path", "")), str(exc))
                    )
        else:
            self._sources = self._load_from_semantic_dir()
            if not self._sources:
                self._sources = self._scan_directory()

    @property
    def errors(self) -> list[SourceError]:
        return list(self._errors)

    def get(self, source_id: str) -> SourceDeclaration | None:
        return self._sources.get(source_id)

    def all_sources(self) -> dict[str, SourceDeclaration]:
        return dict(self._sources)

    def resolve_path(self, source_id: str) -> Path | None:
        decl = self._sources.get(source_id)
        if decl is None:
            return None
        if decl.data_files:
            return decl.data_files[0]
        if decl.path and decl.path.exists():
            return decl.path
        if decl.file_pattern:
            candidate = self._data_root / decl.file_pattern
            if candidate.exists():
                return candidate
        for prefix in ("", "mock_"):
            for ext in (".json", ".csv", ".jsonl"):
                candidate = self._data_root / f"{prefix}{source_id}{ext}"
                if candidate.exists():
                    return candidate
        return None

    def resolve_data_files(self, source_id: str) -> tuple[Path, ...]:
        decl = self._sources.get(source_id)
        if decl is None:
            return ()
        if decl.data_files:
            return decl.data_files
        path = self.resolve_path(source_id)
        return (path,) if path else ()

    def to_metadata(self) -> dict[str, SourceMetadata]:
        """Convert declarations to legacy SourceMetadata for backward compat."""
        result: dict[str, SourceMetadata] = {}
        for source_id, decl in self._sources.items():
            result[source_id] = self._decl_to_metadata(decl)
        return result

    # --- internals ---

    def _parse_source(self, source_id: str, spec: dict) -> SourceDeclaration:
        rel_path = Path(spec["path"]) if "path" in spec else Path("")
        resolved_path = self._data_root / rel_path if not rel_path.is_absolute() else rel_path

        source_type = spec.get("type")
        if source_type is None and resolved_path.exists():
            source_type = detect_format(resolved_path)
        elif source_type is None:
            source_type = "json"
        if source_type not in _VALID_TYPES:
            raise ValueError(
                f"Unknown source type '{source_type}' for source '{source_id}'. "
                f"Valid types: {', '.join(sorted(_VALID_TYPES))}"
            )

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
        if not metrics and resolved_path.exists():
            inferred = infer_metrics(resolved_path, source_type)
            metrics = tuple(
                MetricSpec(
                    name=m["name"],
                    column=m.get("column", ""),
                    aggregation=m.get("aggregation", "count"),
                )
                for m in inferred
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

        fields_meta = {}
        for col, fm in spec.get("metadata", {}).get("fields", {}).items():
            fields_meta[col] = FieldMetadata(
                column=col,
                meaning=fm.get("meaning", ""),
                unit=fm.get("unit", ""),
                aliases=tuple(fm.get("aliases", [])),
                mapping=dict(fm.get("mapping", {})),
                description=fm.get("description", ""),
            )

        if not fields_meta and resolved_path.exists():
            fields_meta = self._load_sidecar_metadata(resolved_path)
        if not fields_meta and resolved_path.exists():
            fields_meta = self._auto_match_fields(resolved_path, source_type)

        return SourceDeclaration(
            source_id=source_id,
            type=source_type,
            path=resolved_path,
            description=spec.get("description", ""),
            schema=spec.get("schema", {}),
            metrics=metrics,
            entities=entities,
            fields=fields_meta,
            example_questions=tuple(spec.get("example_questions", [])),
            file_pattern=spec.get("file_pattern", spec.get("path", "")),
        )

    def _scan_directory(self) -> dict[str, SourceDeclaration]:
        result: dict[str, SourceDeclaration] = {}
        if not self._data_root.exists():
            return result
        for entry in sorted(self._data_root.iterdir()):
            if entry.is_dir():
                meta_file = entry / "metadata.yml"
                if not meta_file.exists():
                    meta_file = entry / "metadata.yaml"
                if meta_file.exists():
                    source_id = entry.name.lower().replace("-", "_").replace(" ", "_")
                    try:
                        result[source_id] = self._load_directory_source(source_id, entry, meta_file)
                    except Exception as exc:
                        self._errors.append(SourceError(source_id, str(entry), str(exc)))
                    continue
            if not entry.is_file() or entry.suffix.lower() not in _DATA_EXTENSIONS:
                continue
            f = entry
            source_id = f.stem.lower().replace("-", "_").replace(" ", "_")
            try:
                source_type = detect_format(f)
                inferred = infer_metrics(f, source_type)
                metrics = tuple(
                    MetricSpec(
                        name=m["name"],
                        column=m.get("column", ""),
                        aggregation=m.get("aggregation", "count"),
                    )
                    for m in inferred
                )
                fields_meta = self._load_sidecar_metadata(f)
                if not fields_meta:
                    fields_meta = self._auto_match_fields(f, source_type)
                result[source_id] = SourceDeclaration(
                    source_id=source_id,
                    type=source_type,
                    path=f,
                    description=f.stem,
                    metrics=metrics,
                    fields=fields_meta,
                    file_pattern=f.name,
                    data_files=(f,),
                )
            except Exception as exc:
                self._errors.append(SourceError(source_id, str(f), str(exc)))
        return result

    def _load_directory_source(
        self, source_id: str, directory: Path, meta_file: Path,
    ) -> SourceDeclaration:
        import yaml

        with open(meta_file, encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        source_type = meta.get("type", "json")
        if source_type not in _VALID_TYPES:
            raise ValueError(
                f"Unknown source type '{source_type}' in {meta_file}. "
                f"Valid types: {', '.join(sorted(_VALID_TYPES))}"
            )

        ext_map = {"json": ".json", "csv": ".csv", "jsonl": ".jsonl"}
        ext = ext_map.get(source_type, ".json")
        data_files = tuple(sorted(directory.glob(f"*{ext}")))

        if not data_files:
            raise FileNotFoundError(f"No {ext} files in {directory}")

        metrics = tuple(
            MetricSpec(
                name=m["name"],
                column=m.get("column", ""),
                aggregation=m.get("aggregation", "count"),
                unit=m.get("unit", ""),
                aliases=tuple(m.get("aliases", [])),
                compute=m.get("compute", ""),
            )
            for m in meta.get("metrics", [])
        )
        if not metrics and data_files:
            inferred = infer_metrics(data_files[0], source_type)
            metrics = tuple(
                MetricSpec(
                    name=m["name"],
                    column=m.get("column", ""),
                    aggregation=m.get("aggregation", "count"),
                )
                for m in inferred
            )

        fields_meta: dict[str, FieldMetadata] = {}
        for col, fm in meta.get("fields", {}).items():
            fields_meta[col] = FieldMetadata(
                column=col,
                meaning=fm.get("meaning", ""),
                unit=fm.get("unit", ""),
                aliases=tuple(fm.get("aliases", [])),
                mapping=dict(fm.get("mapping", {})),
                description=fm.get("description", ""),
            )
        if not fields_meta and data_files:
            fields_meta = self._auto_match_fields(data_files[0], source_type)

        return SourceDeclaration(
            source_id=source_id,
            type=source_type,
            path=directory,
            description=meta.get("description", directory.name),
            schema=meta.get("schema", {}),
            metrics=metrics,
            fields=fields_meta,
            example_questions=tuple(meta.get("example_questions", [])),
            file_pattern="",
            data_files=data_files,
        )

    def _load_sidecar_metadata(self, data_path: Path) -> dict[str, FieldMetadata]:
        sidecar = data_path.with_suffix(".meta.yml")
        if not sidecar.exists():
            sidecar = data_path.with_suffix(".meta.yaml")
        if not sidecar.exists():
            return {}
        try:
            import yaml

            with open(sidecar, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return {}
        fields_meta: dict[str, FieldMetadata] = {}
        for col, fm in data.get("fields", {}).items():
            fields_meta[col] = FieldMetadata(
                column=col,
                meaning=fm.get("meaning", ""),
                unit=fm.get("unit", ""),
                aliases=tuple(fm.get("aliases", [])),
                mapping=dict(fm.get("mapping", {})),
                description=fm.get("description", ""),
            )
        return fields_meta

    def _auto_match_fields(self, data_path: Path, source_type: str) -> dict[str, FieldMetadata]:
        try:
            from petfish_bi_cli.config.auto_detect import _extract_json_items

            if source_type == "csv":
                import csv

                with open(data_path, encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    columns = reader.fieldnames or []
            else:
                items = _extract_json_items(data_path, source_type)
                columns = list(items[0].keys()) if items and isinstance(items[0], dict) else []
        except Exception:
            return {}
        fields_meta: dict[str, FieldMetadata] = {}
        for col in columns:
            matched = self._field_mapper.match(col)
            if matched:
                meaning, meta = matched
                fields_meta[col] = FieldMetadata(
                    column=col,
                    meaning=meaning,
                    unit=meta.get("unit", ""),
                )
        return fields_meta

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
