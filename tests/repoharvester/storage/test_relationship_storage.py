"""Tests for relationship persistence, migration, and exact queries."""

from __future__ import annotations

import sqlite3

from repoharvester import HarvestRelationship, ResolutionState
from repoharvester.storage import SCHEMA_VERSION, SQLiteHarvestStore


def _relationship(**overrides) -> HarvestRelationship:
    values = {
        "source_repository": "repo",
        "source_revision": "a" * 40,
        "source_path": "src/a.ts",
        "source_unit_kind": "file",
        "source_unit_identity": "",
        "relationship_kind": "imports",
        "target_path": "src/b.ts",
        "target_unit_kind": "file",
        "target_unit_identity": "",
        "literal_target": "'./b'",
        "resolution_state": ResolutionState.EXACT,
        "start_byte": 0,
        "end_byte": 24,
        "start_row": 0,
        "start_column": 0,
        "end_row": 0,
        "end_column": 24,
        "extractor_name": "tree-sitter-typescript",
        "extractor_version": "0.21.2",
    }
    values.update(overrides)
    return HarvestRelationship(**values)


def test_relationship_upsert_is_idempotent_and_queryable(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    relation = _relationship()

    assert store.upsert_relationships([relation, relation]) == 2
    assert store.query_relationships(relationship_kind="imports") == [relation]
    assert store.query_relationships(target_path="src/b.ts", resolution_state=ResolutionState.EXACT) == [relation]


def test_schema_v2_migrates_to_relationship_schema_without_losing_records(tmp_path) -> None:
    database = tmp_path / "harvest.sqlite3"
    store = SQLiteHarvestStore(database)
    store.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 2")

    store.initialize()
    assert store.query_relationships() == []
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='harvest_relationships'"
        ).fetchone() == ("harvest_relationships",)
