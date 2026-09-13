"""Deterministic top-level symbol extraction for supported languages."""

from __future__ import annotations

import hashlib
from typing import Optional

import tree_sitter_c_sharp as tscsharp
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from repoharvester.models import HarvestRecord

TYPESCRIPT_SYMBOL_RULESET = "typescript-symbol-v1"
CSHARP_SYMBOL_RULESET = "csharp-symbol-v1"

_TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")
_TSX_LANGUAGE = Language(tstypescript.language_tsx(), "tsx")
_CSHARP_LANGUAGE = Language(tscsharp.language(), "c_sharp")
_TYPESCRIPT_DECLARATION_KINDS = {
    "function_declaration": "function",
    "class_declaration": "class",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "enum_declaration": "enum",
}
_CSHARP_DECLARATION_KINDS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "struct_declaration": "struct",
    "record_declaration": "record",
    "enum_declaration": "enum",
    "delegate_declaration": "delegate",
}
_CSHARP_NAMESPACE_KINDS = {
    "namespace_declaration",
    "file_scoped_namespace_declaration",
}


class TypeScriptParseError(ValueError):
    """Raised when the pinned TypeScript grammar cannot parse a file exactly."""


class CSharpParseError(ValueError):
    """Raised when the pinned C# grammar cannot parse a file exactly."""


def _language_for_path(path: str) -> Language:
    """Select the deterministic TypeScript Tree-sitter grammar from the file suffix."""
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
        raise TypeScriptParseError(message)

    records: list[HarvestRecord] = []
    for node in tree.root_node.named_children:
        records.extend(_typescript_records_from_top_level_node(node, source=source, file_record=file_record))
    return records


def build_csharp_symbol_records(file_record: HarvestRecord) -> list[HarvestRecord]:
    """Extract RAW C# type declarations from file or namespace scope."""
    if file_record.unit_kind != "file" or file_record.language != "C#":
        return []

    source = file_record.representation.encode("utf-8")
    parser = Parser()
    parser.set_language(_CSHARP_LANGUAGE)
    tree = parser.parse(source)
    if tree.root_node.has_error:
        message = f"cannot deterministically extract C# symbols from parse-error file: {file_record.path}"
        raise CSharpParseError(message)

    records: list[HarvestRecord] = []
    for node in tree.root_node.named_children:
        records.extend(_csharp_records_from_scope_node(node, source=source, file_record=file_record))
    return records


def _typescript_records_from_top_level_node(
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
                ruleset=TYPESCRIPT_SYMBOL_RULESET,
                identity_prefix="typescript",
            )
            for declarator in declaration.named_children
            if declarator.type == "variable_declarator"
        ]

    symbol_kind = _TYPESCRIPT_DECLARATION_KINDS.get(declaration.type)
    if symbol_kind is None:
        return []
    return [
        _record_for_node(
            declaration,
            symbol_kind=symbol_kind,
            source=source,
            file_record=file_record,
            ruleset=TYPESCRIPT_SYMBOL_RULESET,
            identity_prefix="typescript",
        )
    ]


def _csharp_records_from_scope_node(
    node: Node,
    *,
    source: bytes,
    file_record: HarvestRecord,
) -> list[HarvestRecord]:
    symbol_kind = _CSHARP_DECLARATION_KINDS.get(node.type)
    if symbol_kind is not None:
        return [
            _record_for_node(
                node,
                symbol_kind=symbol_kind,
                source=source,
                file_record=file_record,
                ruleset=CSHARP_SYMBOL_RULESET,
                identity_prefix="csharp",
                name_node=_csharp_name_node(node),
            )
        ]

    if node.type not in _CSHARP_NAMESPACE_KINDS and node.type != "declaration_list":
        return []

    records: list[HarvestRecord] = []
    for child in node.named_children:
        records.extend(_csharp_records_from_scope_node(child, source=source, file_record=file_record))
    return records


def _csharp_name_node(node: Node) -> Optional[Node]:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return name_node
    for child in node.named_children:
        if child.type == "identifier":
            return child
    return None


def _unwrap_export(node: Node) -> Node:
    if node.type != "export_statement":
        return node
    for child in node.named_children:
        if child.type in _TYPESCRIPT_DECLARATION_KINDS or child.type == "lexical_declaration":
            return child
    return node


def _record_for_node(
    node: Node,
    *,
    symbol_kind: str,
    source: bytes,
    file_record: HarvestRecord,
    ruleset: str,
    identity_prefix: str,
    name_node: Optional[Node] = None,
) -> HarvestRecord:
    resolved_name_node = name_node or node.child_by_field_name("name")
    if resolved_name_node is None:
        message = f"{node.type} at byte {node.start_byte} has no deterministic name"
        raise ValueError(message)

    symbol_name = source[resolved_name_node.start_byte : resolved_name_node.end_byte].decode("utf-8")
    representation_bytes = source[node.start_byte : node.end_byte]
    representation = representation_bytes.decode("utf-8")
    unit_identity = f"{identity_prefix}:{symbol_kind}:{symbol_name}:{node.start_byte}:{node.end_byte}"
    tags = tuple(sorted(set(file_record.tags) | {"unit:symbol", f"symbol:{symbol_kind}"}))

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
        tag_ruleset=ruleset,
        unit_identity=unit_identity,
        symbol_name=symbol_name,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_row=node.start_point[0],
        start_column=node.start_point[1],
        end_row=node.end_point[0],
        end_column=node.end_point[1],
    )
