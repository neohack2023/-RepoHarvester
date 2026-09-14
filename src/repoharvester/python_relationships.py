"""Deterministic Python containment and import relationships."""

from __future__ import annotations

import ast
import posixpath
from collections import defaultdict
from typing import Iterable

from repoharvester.models import HarvestRecord, HarvestRelationship, ResolutionState

PYTHON_RELATIONSHIP_RULESET = "python-ast-relationships-v1"
EXTRACTOR_NAME = "python-stdlib-ast"
EXTRACTOR_VERSION = "1"


def build_python_relationships(
    records: Iterable[HarvestRecord],
    *,
    skip_source_paths: Iterable[str] = (),
) -> list[HarvestRelationship]:
    """Build exact containment plus conservatively resolved Python imports."""
    materialized = list(records)
    skipped = frozenset(skip_source_paths)
    file_records = [
        record for record in materialized if record.unit_kind == "file" and record.language == "Python"
    ]
    files_by_path = {record.path: record for record in file_records}
    symbols_by_path: dict[str, list[HarvestRecord]] = defaultdict(list)
    for record in materialized:
        if record.path in files_by_path and record.unit_kind.startswith("symbol:"):
            symbols_by_path[record.path].append(record)

    module_paths = _module_path_index(files_by_path)
    relationships: list[HarvestRelationship] = []
    for file_record in file_records:
        for symbol in sorted(symbols_by_path[file_record.path], key=lambda item: item.unit_identity):
            relationships.append(
                HarvestRelationship(
                    source_repository=file_record.source_repository,
                    source_revision=file_record.source_revision,
                    source_path=file_record.path,
                    source_unit_kind=file_record.unit_kind,
                    source_unit_identity=file_record.unit_identity,
                    relationship_kind="contains",
                    target_path=symbol.path,
                    target_unit_kind=symbol.unit_kind,
                    target_unit_identity=symbol.unit_identity,
                    resolution_state=ResolutionState.EXACT,
                    start_byte=symbol.start_byte,
                    end_byte=symbol.end_byte,
                    start_row=symbol.start_row,
                    start_column=symbol.start_column,
                    end_row=symbol.end_row,
                    end_column=symbol.end_column,
                    extractor_name=EXTRACTOR_NAME,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )
        if file_record.path not in skipped:
            relationships.extend(_import_relationships(file_record, files_by_path, module_paths))

    return sorted(relationships, key=_relationship_sort_key)


def _import_relationships(
    file_record: HarvestRecord,
    files_by_path: dict[str, HarvestRecord],
    module_paths: dict[str, str],
) -> list[HarvestRelationship]:
    try:
        tree = ast.parse(file_record.representation, filename=file_record.path)
    except SyntaxError as exc:
        raise ValueError(
            f"cannot deterministically extract relationships from parse-error file: {file_record.path}"
        ) from exc

    relationships: list[HarvestRelationship] = []
    for node in ast.walk(tree):
        literals: list[tuple[str, int]] = []
        if isinstance(node, ast.Import):
            literals.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            literal = "." * node.level + module
            literals.append((literal, node.level))
        else:
            continue

        for literal, level in literals:
            target_path, state = _resolve_module(
                file_record.path,
                literal,
                level,
                files_by_path,
                module_paths,
            )
            target = files_by_path.get(target_path) if target_path else None
            relationships.append(
                HarvestRelationship(
                    source_repository=file_record.source_repository,
                    source_revision=file_record.source_revision,
                    source_path=file_record.path,
                    source_unit_kind=file_record.unit_kind,
                    source_unit_identity=file_record.unit_identity,
                    relationship_kind="imports",
                    target_path=target.path if target else "",
                    target_unit_kind=target.unit_kind if target else "",
                    target_unit_identity=target.unit_identity if target else "",
                    literal_target=literal,
                    resolution_state=state,
                    start_row=node.lineno - 1,
                    start_column=node.col_offset,
                    end_row=(getattr(node, "end_lineno", node.lineno) or node.lineno) - 1,
                    end_column=getattr(node, "end_col_offset", node.col_offset) or node.col_offset,
                    extractor_name=EXTRACTOR_NAME,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )
    return relationships


def _module_path_index(files_by_path: dict[str, HarvestRecord]) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in files_by_path:
        if not path.endswith(".py"):
            continue
        parts = path[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        aliases = [".".join(parts)] if parts else []
        if parts and parts[0] in {"src", "lib"} and len(parts) > 1:
            aliases.append(".".join(parts[1:]))
        for alias in aliases:
            if alias and alias not in index:
                index[alias] = path
    return index


def _resolve_module(
    source_path: str,
    literal: str,
    level: int,
    files_by_path: dict[str, HarvestRecord],
    module_paths: dict[str, str],
) -> tuple[str, ResolutionState]:
    if level == 0:
        target = module_paths.get(literal)
        if target:
            return target, ResolutionState.EXACT
        return "", ResolutionState.EXTERNAL

    package_dir = posixpath.dirname(source_path)
    for _ in range(max(level - 1, 0)):
        package_dir = posixpath.dirname(package_dir)
    module = literal[level:]
    base = posixpath.join(package_dir, *module.split(".")) if module else package_dir
    candidates = [f"{base}.py", posixpath.join(base, "__init__.py")]
    for candidate in candidates:
        normalized = posixpath.normpath(candidate)
        if normalized in files_by_path:
            return normalized, ResolutionState.EXACT
    return "", ResolutionState.UNRESOLVED


def _relationship_sort_key(relationship: HarvestRelationship) -> tuple[object, ...]:
    return (
        relationship.source_repository,
        relationship.source_revision,
        relationship.source_path,
        relationship.source_unit_kind,
        relationship.source_unit_identity,
        relationship.relationship_kind,
        relationship.target_path,
        relationship.literal_target,
        relationship.start_row if relationship.start_row is not None else -1,
        relationship.start_column if relationship.start_column is not None else -1,
    )
