"""Tests for deterministic TypeScript code-unit extraction."""

from __future__ import annotations

import hashlib

from repoharvester import HarvestRecord, QualificationState, build_typescript_symbol_records


def _file_record(source: str) -> HarvestRecord:
    source_bytes = source.encode("utf-8")
    digest = hashlib.sha256(source_bytes).hexdigest()
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path="src/example.ts",
        unit_kind="file",
        language="TypeScript",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
        tags=("language:TypeScript", "path-component:src", "role:source"),
        tag_ruleset="path-baseline-v1",
    )


def test_extracts_named_top_level_typescript_units_with_exact_spans() -> None:
    source = """export const RATE = 0.5;
export function score(value: number): number {
  return value * RATE;
}
interface Item { value: number }
type ItemId = string;
class Store { get(): number { return 1; } }
enum Mode { A, B }
"""
    file_record = _file_record(source)

    records = build_typescript_symbol_records(file_record)

    assert [(record.unit_kind, record.symbol_name) for record in records] == [
        ("symbol:variable", "RATE"),
        ("symbol:function", "score"),
        ("symbol:interface", "Item"),
        ("symbol:type", "ItemId"),
        ("symbol:class", "Store"),
        ("symbol:enum", "Mode"),
    ]
    assert all(record.qualification_state == QualificationState.RAW for record in records)
    assert all(record.source_sha256 == file_record.source_sha256 for record in records)
    assert all(record.unit_identity for record in records)
    assert all("unit:symbol" in record.tags for record in records)

    for record in records:
        assert record.start_byte is not None
        assert record.end_byte is not None
        assert record.start_row is not None
        assert record.end_row is not None
        extracted = source.encode("utf-8")[record.start_byte : record.end_byte].decode("utf-8")
        assert extracted == record.representation
        assert hashlib.sha256(extracted.encode("utf-8")).hexdigest() == record.representation_sha256


def test_ignores_nested_methods_and_non_typescript_files() -> None:
    source = "class Store { get(): number { return 1; } }\n"
    records = build_typescript_symbol_records(_file_record(source))
    assert [(record.unit_kind, record.symbol_name) for record in records] == [("symbol:class", "Store")]

    markdown = _file_record("# docs\n")
    markdown = HarvestRecord(**{**markdown.__dict__, "language": "Markdown", "path": "README.md"})
    assert build_typescript_symbol_records(markdown) == []
