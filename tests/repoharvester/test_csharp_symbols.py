"""Tests for deterministic C# code-unit extraction."""

from __future__ import annotations

import hashlib

import pytest

from repoharvester import (
    CSharpParseError,
    HarvestRecord,
    QualificationState,
    build_csharp_symbol_records,
)


def _file_record(source: str, path: str = "src/Example.cs") -> HarvestRecord:
    source_bytes = source.encode("utf-8")
    digest = hashlib.sha256(source_bytes).hexdigest()
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="b" * 40,
        path=path,
        unit_kind="file",
        language="C#",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
        tags=("language:C#", "path-component:src", "role:source"),
        tag_ruleset="path-baseline-v1",
    )


def test_extracts_namespace_scoped_csharp_type_units_with_exact_spans() -> None:
    source = """namespace Acme.Tools
{
    public class Runner { public int Run() => 1; }
    internal interface IClock { }
    public struct Point { public int X; }
    public record Receipt(string Id);
    public enum Mode { A, B }
    public delegate int Transform(int value);
}
"""

    records = build_csharp_symbol_records(_file_record(source))

    assert [(record.unit_kind, record.symbol_name) for record in records] == [
        ("symbol:class", "Runner"),
        ("symbol:interface", "IClock"),
        ("symbol:struct", "Point"),
        ("symbol:record", "Receipt"),
        ("symbol:enum", "Mode"),
        ("symbol:delegate", "Transform"),
    ]
    assert all(record.qualification_state == QualificationState.RAW for record in records)
    assert all(record.tag_ruleset == "csharp-symbol-v1" for record in records)
    assert all(record.source_sha256 for record in records)
    assert all("unit:symbol" in record.tags for record in records)

    for record in records:
        assert record.start_byte is not None
        assert record.end_byte is not None
        extracted = source.encode("utf-8")[record.start_byte : record.end_byte].decode("utf-8")
        assert extracted == record.representation
        assert hashlib.sha256(extracted.encode("utf-8")).hexdigest() == record.representation_sha256


def test_file_scoped_namespace_is_supported_but_nested_members_are_not_units() -> None:
    source = """namespace Acme.Tools;
public class Outer
{
    public class Nested { }
    public int Run() => 1;
}
"""

    records = build_csharp_symbol_records(_file_record(source))

    assert [(record.unit_kind, record.symbol_name) for record in records] == [
        ("symbol:class", "Outer"),
    ]


def test_non_csharp_files_are_ignored_and_parse_errors_fail_closed() -> None:
    source = "public class Example { }\n"
    csharp = _file_record(source)
    markdown = HarvestRecord(**{**csharp.__dict__, "language": "Markdown", "path": "README.md"})

    assert build_csharp_symbol_records(markdown) == []

    with pytest.raises(CSharpParseError):
        build_csharp_symbol_records(_file_record("public class Broken {\n"))
