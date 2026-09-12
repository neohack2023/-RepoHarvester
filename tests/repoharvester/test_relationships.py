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
        source_repository="repo",
        source_revision="a" * 40,
        path=path,
        unit_kind="file",
        language="TypeScript",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
    )


def _json_file(path: str, source: str) -> HarvestRecord:
    digest = hashlib.sha256(source.encode()).hexdigest()
    return HarvestRecord(
        source_repository="repo",
        source_revision="a" * 40,
        path=path,
        unit_kind="file",
        language="JSON",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
    )


def test_builds_contains_and_import_edges_deterministically() -> None:
    a = _file(
        "src/a.ts",
        "import { b } from './b';\n"
        "import React from 'react';\n"
        "export function a() { return b; }\n",
    )
    b = _file("src/b.ts", "export function b() { return 1; }\n")
    records = [a, b, *build_typescript_symbol_records(a), *build_typescript_symbol_records(b)]

    forward = build_typescript_relationships(records)
    reverse = build_typescript_relationships(list(reversed(records)))

    assert forward == reverse
    imports = [item for item in forward if item.relationship_kind == "imports"]
    assert [(item.literal_target, item.resolution_state, item.target_path) for item in imports] == [
        ("'react'", ResolutionState.EXTERNAL, ""),
        ("'./b'", ResolutionState.EXACT, "src/b.ts"),
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


def test_root_tsconfig_alias_resolves_to_harvested_typescript_file() -> None:
    tsconfig = _json_file(
        "tsconfig.json",
        '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}\n',
    )
    app = _file(
        "src/App.ts",
        'import { Button } from "@/components/Button";\n'
        "export function App() { return Button(); }\n",
    )
    button = _file(
        "src/components/Button.ts",
        'export function Button() { return "button"; }\n',
    )
    records = [
        tsconfig,
        app,
        button,
        *build_typescript_symbol_records(app),
        *build_typescript_symbol_records(button),
    ]

    relationships = build_typescript_relationships(records)
    imports = [item for item in relationships if item.relationship_kind == "imports"]

    assert len(imports) == 1
    assert imports[0].literal_target == '"@/components/Button"'
    assert imports[0].resolution_state == ResolutionState.EXACT
    assert imports[0].target_path == "src/components/Button.ts"


def test_unmatched_nonrelative_alias_stays_external() -> None:
    tsconfig = _json_file(
        "tsconfig.json",
        '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}\n',
    )
    source = _file("src/App.ts", 'import x from "@unknown/Button";\n')

    relationships = build_typescript_relationships([tsconfig, source])

    assert len(relationships) == 1
    assert relationships[0].resolution_state == ResolutionState.EXTERNAL
    assert relationships[0].target_path == ""


def test_matched_alias_without_harvested_target_is_unresolved() -> None:
    tsconfig = _json_file(
        "tsconfig.json",
        '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}\n',
    )
    source = _file("src/App.ts", 'import x from "@/missing";\n')

    relationships = build_typescript_relationships([tsconfig, source])

    assert len(relationships) == 1
    assert relationships[0].resolution_state == ResolutionState.UNRESOLVED
    assert relationships[0].target_path == ""


def test_invalid_root_tsconfig_fails_closed_to_external() -> None:
    tsconfig = _json_file("tsconfig.json", "{not-json}\n")
    source = _file("src/App.ts", 'import x from "@/components/Button";\n')
    button = _file("src/components/Button.ts", "export const Button = 1;\n")

    relationships = build_typescript_relationships([tsconfig, source, button])
    imports = [item for item in relationships if item.relationship_kind == "imports"]

    assert len(imports) == 1
    assert imports[0].resolution_state == ResolutionState.EXTERNAL
    assert imports[0].target_path == ""


def test_multiple_tsconfig_files_disable_alias_resolution() -> None:
    root = _json_file(
        "tsconfig.json",
        '{"compilerOptions":{"paths":{"@/*":["src/*"]}}}\n',
    )
    nested = _json_file(
        "examples/tsconfig.app.json",
        '{"compilerOptions":{"paths":{"@/*":["examples/src/*"]}}}\n',
    )
    source = _file("src/App.ts", 'import x from "@/components/Button";\n')
    button = _file("src/components/Button.ts", "export const Button = 1;\n")

    relationships = build_typescript_relationships([root, nested, source, button])
    imports = [item for item in relationships if item.relationship_kind == "imports"]

    assert len(imports) == 1
    assert imports[0].resolution_state == ResolutionState.EXTERNAL
    assert imports[0].target_path == ""


def test_root_tsconfig_extends_disables_alias_resolution() -> None:
    root = _json_file(
        "tsconfig.json",
        '{"extends":"./base.json","compilerOptions":{"paths":{"@/*":["src/*"]}}}\n',
    )
    source = _file("src/App.ts", 'import x from "@/components/Button";\n')
    button = _file("src/components/Button.ts", "export const Button = 1;\n")

    relationships = build_typescript_relationships([root, source, button])
    imports = [item for item in relationships if item.relationship_kind == "imports"]

    assert len(imports) == 1
    assert imports[0].resolution_state == ResolutionState.EXTERNAL
    assert imports[0].target_path == ""
