"""Tests for deterministic SQLite harvest persistence and retrieval."""

from __future__ import annotations

import sqlite3

from repoharvester import HarvestRecord, QualificationState
from repoharvester.storage import SCHEMA_VERSION, SQLiteHarvestStore


def _record(**overrides) -> HarvestRecord:
    values = {
        "source_repository": "https://example.invalid/acme/repo.git",
        "source_revision": "a" * 40,
        "path": "src/example.py",
        "unit_kind": "file",
        "language": "Python",
        "source_sha256": "b" * 64,
        "representation_sha256": "c" * 64,
        "representation": "print('hello')",
        "qualification_state": QualificationState.RAW,
        "tags": ("language:Python", "path-component:src", "role:source"),
        "tag_ruleset": "path-baseline-v1",
    }
    values.update(overrides)
    return HarvestRecord(**values)


def test_sqlite_store_round_trips_complete_record(tmp_path) -> None:
    database = tmp_path / "harvest.sqlite3"
    store = SQLiteHarvestStore(database)
    expected = _record()

    assert store.upsert_records([expected]) == 1
    assert store.all_records() == [expected]

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_sqlite_store_upsert_is_idempotent_by_source_identity(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    first = _record()
    updated = _record(
        representation="print('updated')",
        representation_sha256="d" * 64,
        tags=("language:Python", "role:test"),
        qualification_state=QualificationState.TAGGED,
    )

    store.upsert_records([first])
    store.upsert_records([updated])

    assert store.all_records() == [updated]


def test_sqlite_store_keeps_distinct_revisions_and_paths(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    first = _record()
    second_revision = _record(source_revision="e" * 40)
    second_path = _record(path="tests/test_example.py", tags=("language:Python", "role:test"))

    store.upsert_records([second_revision, second_path, first])

    assert store.all_records() == [first, second_path, second_revision]


def test_query_records_filters_exact_provenance_and_fields(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    expected = _record()
    other_revision = _record(source_revision="e" * 40)
    other_repository = _record(source_repository="https://example.invalid/other/repo.git")
    other_language = _record(path="src/readme.md", language="Markdown", tags=("language:Markdown", "role:source"))
    store.upsert_records([other_revision, other_repository, other_language, expected])

    assert store.query_records(
        source_repository=expected.source_repository,
        source_revision=expected.source_revision,
        path=expected.path,
        unit_kind="file",
        language="Python",
        qualification_state=QualificationState.RAW,
    ) == [expected]


def test_query_records_requires_every_requested_tag(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    source = _record()
    test = _record(
        path="tests/test_example.py",
        tags=("language:Python", "path-component:tests", "role:test"),
    )
    store.upsert_records([test, source])

    assert store.query_records(tags=("language:Python", "role:source")) == [source]
    assert store.query_records(tags=("language:Python", "role:test")) == [test]
    assert store.query_records(tags=("role:source", "role:test")) == []


def test_query_records_combines_provenance_and_tags_without_ranking(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    first = _record(path="src/a.py")
    second = _record(path="src/b.py")
    other_revision = _record(path="src/c.py", source_revision="e" * 40)
    store.upsert_records([second, other_revision, first])

    assert store.query_records(
        source_repository=first.source_repository,
        source_revision=first.source_revision,
        tags=("role:source",),
    ) == [first, second]
