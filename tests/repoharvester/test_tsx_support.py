"""Regression tests for deterministic TSX harvesting."""

from __future__ import annotations

import hashlib

from repoharvester import (
    HarvestRecord,
    ResolutionState,
    build_typescript_relationships,
    build_typescript_symbol_records,
)


def _file(path: str, source: str) -> HarvestRecord:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path=path,
        unit_kind="file",
        language="TypeScript",
        source_sha256=digest,
        representation_sha256=digest,
        representation=source,
    )


def test_extracts_top_level_symbol_from_tsx() -> None:
    record = _file(
        "src/App.tsx",
        "export function App() { return <main>Hello</main>; }\n",
    )

    symbols = build_typescript_symbol_records(record)

    assert [(item.unit_kind, item.symbol_name) for item in symbols] == [
        ("symbol:function", "App")
    ]
    assert symbols[0].representation == "function App() { return <main>Hello</main>; }"


def test_extracts_tsx_imports_and_resolves_tsx_targets() -> None:
    app = _file(
        "src/App.tsx",
        "import { Panel } from './Panel';\nexport function App() { return <Panel />; }\n",
    )
    panel = _file(
        "src/Panel.tsx",
        "export function Panel() { return <section />; }\n",
    )
    records = [
        app,
        panel,
        *build_typescript_symbol_records(app),
        *build_typescript_symbol_records(panel),
    ]

    relationships = build_typescript_relationships(records)
    imports = [item for item in relationships if item.relationship_kind == "imports"]

    assert len(imports) == 1
    assert imports[0].literal_target == "'./Panel'"
    assert imports[0].resolution_state == ResolutionState.EXACT
    assert imports[0].target_path == "src/Panel.tsx"
