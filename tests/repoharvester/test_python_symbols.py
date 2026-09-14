"""Tests for deterministic Python symbol harvesting."""

from __future__ import annotations

import hashlib

import pytest

from repoharvester.models import HarvestRecord
from repoharvester.python_symbols import PythonParseError, build_python_symbol_records


def _file(source: str) -> HarvestRecord:
    payload = source.encode("utf-8")
    return HarvestRecord(
        source_repository="https://example.invalid/python.git",
        source_revision="a" * 40,
        path="src/pkg/module.py",
        unit_kind="file",
        language="Python",
        source_sha256=hashlib.sha256(payload).hexdigest(),
        representation_sha256=hashlib.sha256(payload).hexdigest(),
        representation=source,
        tags=("language:Python", "role:source"),
        tag_ruleset="path-baseline-v1",
    )


def test_extracts_functions_classes_methods_and_constants() -> None:
    source = """MAX_RETRIES = 3\n\ndef helper(value: int) -> int:\n    return value + 1\n\nclass Worker:\n    def run(self, value: int) -> int:\n        return helper(value)\n"""

    records = build_python_symbol_records(_file(source))

    assert [(record.unit_kind, record.symbol_name) for record in records] == [
        ("symbol:constant", "MAX_RETRIES"),
        ("symbol:function", "helper"),
        ("symbol:class", "Worker"),
        ("symbol:method", "run"),
    ]
    assert all(record.source_revision == "a" * 40 for record in records)
    assert all("unit:symbol" in record.tags for record in records)
    assert "return helper(value)" in records[-1].representation


def test_parse_error_fails_closed() -> None:
    with pytest.raises(PythonParseError):
        build_python_symbol_records(_file("def broken(:\n    pass\n"))
