"""Tests for code-unit storage identity and schema v2 migration."""

from __future__ import annotations

import sqlite3

from repoharvester import HarvestRecord, QualificationState
from repoharvester.storage import SCHEMA_VERSION, SQLiteHarvestStore


def _symbol(name: str, start: int, end: int) -> HarvestRecord:
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path="src/example.ts",
        unit_kind="symbol:function",
        unit_identity=f"typescript:function:{name}:{start}:{end}",
        symbol_name=name,
        language="TypeScript",
        source_sha256="b" * 64,
        representation_sha256=("c" if name == "first" else "d") * 64,
        representation=f"function {name}() {{}}",
        qualification_state=QualificationState.RAW,
        tags=("language:TypeScript", "role:source", "symbol:function", "unit:symbol"),
        tag_ruleset="typescript-symbol-v1",
        start_byte=start,
        end_byte=end,
        start_row=0,
        start_column=start,
        end_row=0,
        end_column=end,
    )


def test_store_keeps_multiple_symbols_in_same_file_and_queries_exact_name(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    first = _symbol("first", 0, 19)
    second = _symbol("second", 20, 40)

    assert store.upsert_records([second, first]) == 2
    assert store.query_records(symbol_name="first") == [first]
    assert store.query_records(path="src/example.ts", unit_kind="symbol:function") == [first, second]


def test_schema_v1_migrates_without_losing_file_records_or_tags(tmp_path) -> None:
    database = tmp_path / "harvest.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE harvest_records (
                id INTEGER PRIMARY KEY,
                source_repository TEXT NOT NULL,
                source_revision TEXT NOT NULL,
                path TEXT NOT NULL,
                unit_kind TEXT NOT NULL,
                language TEXT,
                source_sha256 TEXT NOT NULL,
                representation_sha256 TEXT NOT NULL,
                representation TEXT NOT NULL,
                qualification_state TEXT NOT NULL,
                tag_ruleset TEXT,
                UNIQUE (source_repository, source_revision, path, unit_kind)
            );
            CREATE TABLE harvest_record_tags (
                record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                PRIMARY KEY (record_id, tag)
            );
            INSERT INTO harvest_records VALUES (
                1, 'repo', 'rev', 'src/a.py', 'file', 'Python',
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                'print(1)', 'RAW', 'path-baseline-v1'
            );
            INSERT INTO harvest_record_tags VALUES (1, 'role:source');
            PRAGMA user_version = 1;
            """
        )

    store = SQLiteHarvestStore(database)
    records = store.all_records()

    assert len(records) == 1
    assert records[0].path == "src/a.py"
    assert records[0].unit_identity == ""
    assert records[0].tags == ("role:source",)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
