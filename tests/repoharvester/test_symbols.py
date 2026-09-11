from __future__ import annotations

import hashlib

import pytest

from repoharvester import HarvestRecord, QualificationState, build_typescript_symbol_records

pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_typescript")


def _file_record(source: str) -> HarvestRecord:
    source_bytes = source.encode("utf-8")
    digest = hashlib.sha256(source_bytes).hexdigest()
    return HarvestRecord(
        source_repository="https://example.com/repo.git",
        source_revision="a" * 40,
        path="src/example.ts",
        unit_kind="file",
        language="TypeScript",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
        tags=("role:source", "language:typescript"),
        tag_ruleset="path-baseline-v1",
    )


def test_extracts_named_typescript_code_units_with_locations_and_hashes() -> None:
    source = """export class Greeter {
  greet(name: string): string { return name; }
}
export function add(a: number, b: number): number { return a + b; }
export const double = (value: number) => value * 2;
export interface Shape { area(): number; }
export type Identifier = string;
export enum Mode { A, B }
"""
    file_record = _file_record(source)

    records = build_typescript_symbol_records([file_record])
    names = {record.symbol_name for record in records}

    assert {"Greeter", "Greeter.greet", "add", "double", "Shape", "Identifier", "Mode"} <= names
    assert {record.qualification_state for record in records} == {QualificationState.RAW}
    assert all(record.unit_kind == "symbol" for record in records)
    assert all(record.source_sha256 == file_record.source_sha256 for record in records)
    assert all(record.unit_identity for record in records)
    assert all(record.start_byte is not None and record.end_byte is not None for record in records)
    assert all(record.start_line is not None and record.start_line >= 1 for record in records)
    assert all(record.representation_sha256 == hashlib.sha256(record.representation.encode("utf-8")).hexdigest() for record in records)


def test_symbol_identity_is_deterministic_for_same_source() -> None:
    source = "export function stable(value: number): number { return value; }\n"
    file_record = _file_record(source)

    first = build_typescript_symbol_records([file_record])
    second = build_typescript_symbol_records([file_record])

    assert first == second
