from __future__ import annotations

import sqlite3
from pathlib import Path

from repoharvester import HarvestRecord, QualificationState
from repoharvester.storage import SCHEMA_VERSION, SQLiteHarvestStore


def _symbol(identity: str, name: str, start: int, end: int) -> HarvestRecord:
    return HarvestRecord(
        source_repository="https://example.com/repo.git",
        source_revision="b" * 40,
        path="src/example.ts",
        unit_kind="symbol",
        unit_identity=identity,
        symbol_name=name,
        language="TypeScript",
        source_sha256="1" * 64,
        representation_sha256="2" * 64,
        representation=f"function {name}() {{}}",
        qualification_state=QualificationState.RAW,
        tags=("symbol:function", "unit:symbol"),
        tag_ruleset="path-baseline-v1+typescript-symbol-v1",
        start_byte=start,
        end_byte=end,
        start_line=1,
        start_column=start + 1,
        end_line=1,
        end_column=end + 1,
    )


def test_multiple_symbols_share_path_without_identity_collision(tmp_path: Path) -> None:
    database = tmp_path / "harvest.sqlite3"
    store = SQLiteHarvestStore(database)
    first = _symbol("function:first@0:20", "first", 0, 20)
    second = _symbol("function:second@21:42", "second", 21, 42)

    assert store.upsert_records([first, second]) == 2

    loaded = store.query_records(
        source_repository=first.source_repository,
        source_revision=first.source_revision,
        path=first.path,
        unit_kind="symbol",
    )
    assert loaded == [first, second]
    assert store.query_records(symbol_name="second") == [second]
    assert store.query_records(unit_identity=first.unit_identity) == [first]


def test_schema_v1_database_migrates_without_losing_file_records(tmp_path: Path) -> None:
    database = tmp_path / "legacy.sqlite3"
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
            INSERT INTO harvest_records (
                id, source_repository, source_revision, path, unit_kind, language,
                source_sha256, representation_sha256, representation,
                qualification_state, tag_ruleset
            ) VALUES (
                1, 'https://example.com/repo.git', 'cccccccccccccccccccccccccccccccccccccccc',
                'src/legacy.ts', 'file', 'TypeScript',
                '1111111111111111111111111111111111111111111111111111111111111111',
                '2222222222222222222222222222222222222222222222222222222222222222',
                'export const legacy = true;', 'RAW', 'path-baseline-v1'
            );
            INSERT INTO harvest_record_tags(record_id, tag) VALUES (1, 'role:source');
            PRAGMA user_version = 1;
            """
        )

    store = SQLiteHarvestStore(database)
    store.initialize()
    records = store.all_records()

    assert len(records) == 1
    assert records[0].path == "src/legacy.ts"
    assert records[0].unit_identity == ""
    assert records[0].tags == ("role:source",)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
