"""Deterministic TypeScript symbol extraction from file harvest records."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from typing import Iterable

from repoharvester.models import HarvestRecord, QualificationState

TYPESCRIPT_SYMBOL_RULESET = "typescript-symbol-v1"

_SYMBOL_NODE_KINDS = {
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "class_declaration": "class",
    "abstract_class_declaration": "class",
    "interface_declaration": "interface",
    "type_alias_declaration": "type_alias",
    "enum_declaration": "enum",
    "method_definition": "method",
    "method_signature": "method_signature",
    "abstract_method_signature": "method_signature",
}
_CALLABLE_VALUE_TYPES = {"arrow_function", "function_expression", "generator_function"}


def build_typescript_symbol_records(file_records: Iterable[HarvestRecord]) -> list[HarvestRecord]:
    """Extract deterministic RAW symbol records from TypeScript/TSX file records."""
    records: list[HarvestRecord] = []
    for file_record in file_records:
        if file_record.unit_kind != "file" or file_record.language != "TypeScript":
            continue
        records.extend(_extract_file_symbols(file_record))
    return sorted(records, key=_record_sort_key)


def _extract_file_symbols(file_record: HarvestRecord) -> list[HarvestRecord]:
    try:
        import tree_sitter_typescript as tstypescript
        from tree_sitter import Language, Parser
    except ImportError as exc:  # pragma: no cover - exercised by optional-dependency boundary
        message = (
            "TypeScript symbol extraction requires the 'typescript-symbols' optional dependency"
        )
        raise RuntimeError(message) from exc

    suffix = PurePosixPath(file_record.path).suffix.lower()
    language_capsule = (
        tstypescript.language_tsx() if suffix == ".tsx" else tstypescript.language_typescript()
    )
    parser = Parser(Language(language_capsule))
    source_bytes = file_record.representation.encode("utf-8")
    tree = parser.parse(source_bytes)
    if tree.root_node.has_error:
        message = f"TypeScript parser reported syntax errors in {file_record.path}"
        raise ValueError(message)

    extracted: list[HarvestRecord] = []
    _walk_symbols(
        tree.root_node,
        source_bytes=source_bytes,
        file_record=file_record,
        parent_name=None,
        output=extracted,
    )
    return extracted


def _walk_symbols(node, *, source_bytes: bytes, file_record: HarvestRecord, parent_name: str | None, output: list[HarvestRecord]) -> None:
    symbol = _symbol_for_node(node, source_bytes=source_bytes, parent_name=parent_name)
    next_parent = parent_name
    if symbol is not None:
        symbol_kind, qualified_name = symbol
        output.append(
            _symbol_record(
                file_record,
                node=node,
                source_bytes=source_bytes,
                symbol_kind=symbol_kind,
                qualified_name=qualified_name,
            )
        )
        next_parent = qualified_name

    for child in node.named_children:
        _walk_symbols(
            child,
            source_bytes=source_bytes,
            file_record=file_record,
            parent_name=next_parent,
            output=output,
        )


def _symbol_for_node(node, *, source_bytes: bytes, parent_name: str | None) -> tuple[str, str] | None:
    symbol_kind = _SYMBOL_NODE_KINDS.get(node.type)
    name_node = None
    if symbol_kind is not None:
        name_node = node.child_by_field_name("name")
    elif node.type == "variable_declarator":
        value_node = node.child_by_field_name("value")
        if value_node is None or value_node.type not in _CALLABLE_VALUE_TYPES:
            return None
        symbol_kind = "callable_variable"
        name_node = node.child_by_field_name("name")
    else:
        return None

    if name_node is None:
        return None
    name = source_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
    qualified_name = f"{parent_name}.{name}" if parent_name else name
    return symbol_kind, qualified_name


def _symbol_record(
    file_record: HarvestRecord,
    *,
    node,
    source_bytes: bytes,
    symbol_kind: str,
    qualified_name: str,
) -> HarvestRecord:
    representation_bytes = source_bytes[node.start_byte : node.end_byte]
    representation = representation_bytes.decode("utf-8")
    unit_identity = f"{symbol_kind}:{qualified_name}@{node.start_byte}:{node.end_byte}"
    tags = tuple(
        sorted(
            set(file_record.tags)
            | {"unit:symbol", f"symbol:{symbol_kind}", "language:typescript"}
        )
    )
    tag_ruleset = TYPESCRIPT_SYMBOL_RULESET
    if file_record.tag_ruleset:
        tag_ruleset = f"{file_record.tag_ruleset}+{TYPESCRIPT_SYMBOL_RULESET}"

    return HarvestRecord(
        source_repository=file_record.source_repository,
        source_revision=file_record.source_revision,
        path=file_record.path,
        unit_kind="symbol",
        language="TypeScript",
        source_sha256=file_record.source_sha256,
        representation_sha256=hashlib.sha256(representation_bytes).hexdigest(),
        representation=representation,
        qualification_state=QualificationState.RAW,
        tags=tags,
        tag_ruleset=tag_ruleset,
        unit_identity=unit_identity,
        symbol_name=qualified_name,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_line=node.start_point.row + 1,
        start_column=node.start_point.column + 1,
        end_line=node.end_point.row + 1,
        end_column=node.end_point.column + 1,
    )


def _record_sort_key(record: HarvestRecord) -> tuple[str, str, int, int, str]:
    return (
        record.source_repository,
        record.path,
        record.start_byte or 0,
        record.end_byte or 0,
        record.unit_identity,
    )
