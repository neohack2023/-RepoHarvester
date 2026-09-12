"""Deterministic TypeScript relationship extraction."""

from __future__ import annotations

import posixpath
from collections import defaultdict
from typing import Iterable

import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from repoharvester.models import HarvestRecord, HarvestRelationship, ResolutionState

TYPESCRIPT_RELATIONSHIP_RULESET = "typescript-relationships-v1"
EXTRACTOR_NAME = "tree-sitter-typescript"
EXTRACTOR_VERSION = "0.21.2"

_TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")
_TSX_LANGUAGE = Language(tstypescript.language_tsx(), "tsx")


def _language_for_path(path: str) -> Language:
    """Select the deterministic Tree-sitter grammar from the file suffix."""
    return _TSX_LANGUAGE if path.lower().endswith(".tsx") else _TYPESCRIPT_LANGUAGE


def build_typescript_relationships(
    records: Iterable[HarvestRecord],
    *,
    skip_source_paths: Iterable[str] = (),
) -> list[HarvestRelationship]:
    """Build deterministic containment and import relationships for TypeScript records.

    ``skip_source_paths`` is used by the generic corpus harvester when the pinned
    parser cannot represent one source file. The file remains available as an
    import target, but no semantic relationships are fabricated from that file.
    """
    materialized = list(records)
    skipped = frozenset(skip_source_paths)
    file_records = [
        record for record in materialized if record.unit_kind == "file" and record.language == "TypeScript"
    ]
    symbols_by_path: dict[str, list[HarvestRecord]] = defaultdict(list)
    files_by_path = {record.path: record for record in file_records}
    for record in materialized:
        if record.path in files_by_path and record.unit_kind.startswith("symbol:"):
            symbols_by_path[record.path].append(record)

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
            relationships.extend(_import_relationships(file_record, files_by_path))

    return sorted(relationships, key=_relationship_sort_key)


def _import_relationships(
    file_record: HarvestRecord,
    files_by_path: dict[str, HarvestRecord],
) -> list[HarvestRelationship]:
    source = file_record.representation.encode("utf-8")
    parser = Parser()
    parser.set_language(_language_for_path(file_record.path))
    tree = parser.parse(source)
    if tree.root_node.has_error:
        message = f"cannot deterministically extract relationships from parse-error file: {file_record.path}"
        raise ValueError(message)

    relationships: list[HarvestRelationship] = []
    for node in tree.root_node.named_children:
        if node.type != "import_statement":
            continue
        string_node = node.child_by_field_name("source") or _first_named_child(node, "string")
        if string_node is None:
            raise ValueError(f"import statement at byte {node.start_byte} has no module specifier")
        literal = source[string_node.start_byte : string_node.end_byte].decode("utf-8")
        module_specifier = _unquote(literal)
        target_path, state = _resolve_module(file_record.path, module_specifier, files_by_path)
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
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                start_row=node.start_point[0],
                start_column=node.start_point[1],
                end_row=node.end_point[0],
                end_column=node.end_point[1],
                extractor_name=EXTRACTOR_NAME,
                extractor_version=EXTRACTOR_VERSION,
            )
        )
    return relationships


def _first_named_child(node: Node, node_type: str) -> Node | None:
    return next((child for child in node.named_children if child.type == node_type), None)


def _unquote(literal: str) -> str:
    if len(literal) >= 2 and literal[0] == literal[-1] and literal[0] in {"'", '"'}:
        return literal[1:-1]
    return literal


def _resolve_module(
    source_path: str,
    module_specifier: str,
    files_by_path: dict[str, HarvestRecord],
) -> tuple[str, ResolutionState]:
    if not module_specifier.startswith("."):
        return "", ResolutionState.EXTERNAL

    base = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), module_specifier))
    candidates = [base]
    if not posixpath.splitext(base)[1]:
        candidates.extend(
            [
                f"{base}.ts",
                f"{base}.tsx",
                posixpath.join(base, "index.ts"),
                posixpath.join(base, "index.tsx"),
            ]
        )
    for candidate in candidates:
        if candidate in files_by_path:
            return candidate, ResolutionState.EXACT
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
        relationship.target_unit_kind,
        relationship.target_unit_identity,
        relationship.literal_target,
        relationship.start_byte if relationship.start_byte is not None else -1,
        relationship.end_byte if relationship.end_byte is not None else -1,
    )
