"""Deterministic Python symbol extraction using the standard-library AST."""

from __future__ import annotations

import ast
import hashlib

from repoharvester.models import HarvestRecord

PYTHON_SYMBOL_RULESET = "python-ast-symbol-v1"


class PythonParseError(ValueError):
    """Raised when Python source cannot be parsed exactly by the runtime AST."""


def build_python_symbol_records(file_record: HarvestRecord) -> list[HarvestRecord]:
    """Extract deterministic Python code-unit records from one harvested file."""
    if file_record.unit_kind != "file" or file_record.language != "Python":
        return []

    source = file_record.representation
    source_bytes = source.encode("utf-8")
    try:
        tree = ast.parse(source, filename=file_record.path)
    except SyntaxError as exc:
        raise PythonParseError(
            f"cannot deterministically extract symbols from parse-error file: {file_record.path}"
        ) from exc

    line_offsets = _line_offsets(source_bytes)
    records: list[HarvestRecord] = []

    def collect(
        body: list[ast.stmt],
        parent: str | None = None,
        *,
        parent_is_class: bool = False,
    ) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                qualified = f"{parent}.{name}" if parent else name
                kind = "method" if parent_is_class else "function"
                records.append(
                    _record_for_node(
                        node,
                        symbol_name=name,
                        qualified_name=qualified,
                        symbol_kind=kind,
                        source=source_bytes,
                        line_offsets=line_offsets,
                        file_record=file_record,
                    )
                )
                collect(node.body, qualified, parent_is_class=False)
                continue

            if isinstance(node, ast.ClassDef):
                name = node.name
                qualified = f"{parent}.{name}" if parent else name
                records.append(
                    _record_for_node(
                        node,
                        symbol_name=name,
                        qualified_name=qualified,
                        symbol_kind="class",
                        source=source_bytes,
                        line_offsets=line_offsets,
                        file_record=file_record,
                    )
                )
                collect(node.body, qualified, parent_is_class=True)
                continue

            if parent is None:
                for name in _module_constant_names(node):
                    records.append(
                        _record_for_node(
                            node,
                            symbol_name=name,
                            qualified_name=name,
                            symbol_kind="constant",
                            source=source_bytes,
                            line_offsets=line_offsets,
                            file_record=file_record,
                        )
                    )

    collect(tree.body)
    return sorted(
        records,
        key=lambda record: (
            record.start_byte if record.start_byte is not None else -1,
            record.unit_identity,
        ),
    )


def _module_constant_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name) and target.id.isupper()]
        return tuple(name for name in names if len(name) > 1)
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        name = node.target.id
        if name.isupper() and len(name) > 1:
            return (name,)
    return ()


def _record_for_node(
    node: ast.AST,
    *,
    symbol_name: str,
    qualified_name: str,
    symbol_kind: str,
    source: bytes,
    line_offsets: list[int],
    file_record: HarvestRecord,
) -> HarvestRecord:
    start_line, start_column = _node_start(node)
    end_line = getattr(node, "end_lineno", None) or start_line
    end_column = getattr(node, "end_col_offset", None)
    if end_column is None:
        end_column = len(source.splitlines(keepends=True)[end_line - 1])

    start_byte = _absolute_offset(line_offsets, start_line, start_column)
    end_byte = _absolute_offset(line_offsets, end_line, end_column)
    representation_bytes = source[start_byte:end_byte]
    representation = representation_bytes.decode("utf-8")
    unit_identity = f"python:{symbol_kind}:{qualified_name}:{start_byte}:{end_byte}"
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
        tag_ruleset=PYTHON_SYMBOL_RULESET,
        unit_identity=unit_identity,
        symbol_name=symbol_name,
        start_byte=start_byte,
        end_byte=end_byte,
        start_row=start_line - 1,
        start_column=start_column,
        end_row=end_line - 1,
        end_column=end_column,
    )


def _node_start(node: ast.AST) -> tuple[int, int]:
    line = getattr(node, "lineno")
    column = getattr(node, "col_offset")
    decorators = getattr(node, "decorator_list", ())
    if decorators:
        first = min(decorators, key=lambda item: (item.lineno, item.col_offset))
        if first.lineno < line:
            return first.lineno, 0
    return line, column


def _line_offsets(source: bytes) -> list[int]:
    offsets = [0]
    total = 0
    for line in source.splitlines(keepends=True):
        total += len(line)
        offsets.append(total)
    return offsets


def _absolute_offset(offsets: list[int], line: int, column: int) -> int:
    return offsets[line - 1] + column
