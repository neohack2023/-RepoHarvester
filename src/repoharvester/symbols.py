"""Deterministic TypeScript top-level symbol extraction."""

from __future__ import annotations

import hashlib

import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from repoharvester.models import HarvestRecord

TYPESCRIPT_SYMBOL_RULESET = "typescript-symbol-v1"

_TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")
_TSX_LANGUAGE = Language(tstypescript.language_tsx(), "tsx")
_DECLARATION_KINDS = {
    "function_declaration": "function",
    "class_declaration": "class",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "enum_declaration": "enum",
}


def _language_for_path(path: str) -> Language:
    """Select the deterministic Tree-sitter grammar from the file suffix."""
    return _TSX_LANGUAGE if path.lower().endswith(".tsx") else _TYPESCRIPT_LANGUAGE


def build_typescript_symbol_records(file_record: HarvestRecord) -> list[HarvestRecord]:
    """Extract RAW top-level TypeScript declarations from one file record."""
    if file_record.unit_kind != "file" or file_record.language != "TypeScript":
        return []

    source = file_record.representation.encode("utf-8")
    parser = Parser()
    parser.set_language(_language_for_path(file_record.path))
    tree = parser.parse(source)
    if tree.root_node.has_error:
        message = f"cannot deterministically extract symbols from parse-error file: {file_record.path}"
        raise ValueError(message)

    records: list[HarvestRecord] = []
    for node in tree.root_node.named_children:
        records.extend(_records_from_top_level_node(node, source=source, file_record=file_record))
    return records


def _records_from_top_level_node(
    node: Node,
    *,
    source: bytes,
    file_record: HarvestRecord,
) -> list[HarvestRecord]:
    declaration = _unwrap_export(node)
    if declaration.type == "lexical_declaration":
        return [
            _record_for_node(
                declarator,
                symbol_kind="variable",
                source=source,
                file_record=file_record,
            )
            for declarator in declaration.named_children
            if declarator.type == "variable_declarator"
        ]

    symbol_kind = _DECLARATION_KINDS.get(declaration.type)
    if symbol_kind is None:
        return []
    return [
        _record_for_node(
            declaration,
            symbol_kind=symbol_kind,
            source=source,
            file_record=file_record,
        )
    ]


def _unwrap_export(node: Node) -> Node:
    if node.type != "export_statement":
        return node
    for child in node.named_children:
        if child.type in _DECLARATION_KINDS or child.type == "lexical_declaration":
            return child
    return node


def _record_for_node(
    node: Node,
    *,
    symbol_kind: str,
    source: bytes,
    file_record: HarvestRecord,
) -> HarvestRecord:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        message = f"{node.type} at byte {node.start_byte} has no deterministic name"
        raise ValueError(message)

    symbol_name = source[name_node.start_byte : name_node.end_byte].decode("utf-8")
    representation_bytes = source[node.start_byte : node.end_byte]
    representation = representation_bytes.decode("utf-8")
    unit_identity = (
        f"typescript:{symbol_kind}:{symbol_name}:"
        f"{node.start_byte}:{node.end_byte}"
    )
    tags = tuple(
        sorted(
            set(file_record.tags)
            | {"unit:symbol", f"symbol:{symbol_kind}"}
        )
    )

    return HarvestRecord(
        source_repository=file_record.source_repository,
        source_revision=file_record.source_revision,
        path=file_record.path,
        unit_kind=f"symbol:{symbol_kind}",
        language=file_record.language,
        source_sha256=file_record.source_sha256,
        representation_sha256=hashlib.sha256(representation_bytes).hexdigest(),
        representation=representation,
        tags=tags,
        tag_ruleset=TYPESCRIPT_SYMBOL_RULESET,
        unit_identity=unit_identity,
        symbol_name=symbol_name,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_row=node.start_point[0],
        start_column=node.start_point[1],
        end_row=node.end_point[0],
        end_column=node.end_point[1],
    )
