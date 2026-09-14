"""Tests for deterministic Python relationships."""

from __future__ import annotations

import hashlib

from repoharvester.models import HarvestRecord, ResolutionState
from repoharvester.python_relationships import build_python_relationships
from repoharvester.python_symbols import build_python_symbol_records


def _file(path: str, source: str) -> HarvestRecord:
    payload = source.encode("utf-8")
    return HarvestRecord(
        source_repository="https://example.invalid/python.git",
        source_revision="b" * 40,
        path=path,
        unit_kind="file",
        language="Python",
        source_sha256=hashlib.sha256(payload).hexdigest(),
        representation_sha256=hashlib.sha256(payload).hexdigest(),
        representation=source,
        tags=("language:Python", "role:source"),
        tag_ruleset="path-baseline-v1",
    )


def test_builds_containment_and_resolves_internal_import() -> None:
    init = _file("src/pkg/__init__.py", "")
    helper = _file("src/pkg/helper.py", "def work():\n    return 1\n")
    main = _file("src/pkg/main.py", "from pkg import helper\n\ndef run():\n    return helper.work()\n")
    records = [init, helper, main]
    records.extend(build_python_symbol_records(helper))
    records.extend(build_python_symbol_records(main))

    relationships = build_python_relationships(records)

    contains = [item for item in relationships if item.relationship_kind == "contains"]
    imports = [item for item in relationships if item.relationship_kind == "imports"]
    assert len(contains) == 2
    assert len(imports) == 1
    assert imports[0].literal_target == "pkg"
    assert imports[0].target_path == "src/pkg/__init__.py"
    assert imports[0].resolution_state == ResolutionState.EXACT


def test_external_import_stays_external() -> None:
    main = _file("src/pkg/main.py", "import sqlite3\n")
    relationships = build_python_relationships([main])
    assert len(relationships) == 1
    assert relationships[0].resolution_state == ResolutionState.EXTERNAL
