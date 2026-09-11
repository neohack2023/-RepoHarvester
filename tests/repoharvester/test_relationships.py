"""Tests for deterministic TypeScript relationship evidence."""

from __future__ import annotations

import hashlib

from repoharvester import (
    HarvestRecord,
    ResolutionState,
    build_typescript_relationships,
    build_typescript_symbol_records,
)


def _file(path: str, source: str) -> HarvestRecord:
    digest = hashlib.sha256(source.encode()).hexdigest()
    return HarvestRecord(
        source_repository="repo", source_revision="a" * 40, path=path,
        unit_kind="file", language="TypeScript", source_sha256=digest,
        representation_sha256=digest, representation=source,
    )


def test_builds_contains_and_import_edges_deterministically() -> None:
    a = _file("src/a.ts", "import { b } from './b';\nimport React from 'react';\nexport function a() { return b; }\n")
    b = _file("src/b.ts", "export function b() { return 1; }\n")
    records = [a, b, *build_typescript_symbol_records(a), *build_typescript_symbol_records(b)]

    forward = build_typescript_relationships(records)
    reverse = build_typescript_relationships(list(reversed(records)))

    assert forward == reverse
    imports = [item for item in forward if item.relationship_kind == "imports"]
    assert [(item.literal_target, item.resolution_state, item.target_path) for item in imports] == [
        ("'./b'", ResolutionState.EXACT, "src/b.ts"),
        ("'react'", ResolutionState.EXTERNAL, ""),
    ]
    contains = [item for item in forward if item.relationship_kind == "contains"]
    assert len(contains) == 2
    assert all(item.resolution_state == ResolutionState.EXACT for item in contains)


def test_unresolved_relative_import_stays_unresolved() -> None:
    source = _file("src/a.ts", "import './missing';\n")
    relationships = build_typescript_relationships([source])
    assert relationships[0].literal_target == "'./missing'"
    assert relationships[0].resolution_state == ResolutionState.UNRESOLVED
    assert relationships[0].target_path == ""
