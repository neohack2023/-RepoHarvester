"""Deterministic SQLite persistence and exact retrieval for harvest records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from repoharvester.models import HarvestRecord, QualificationState

SCHEMA_VERSION = 2

_SCHEMA_V2 = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS harvest_records (
    id INTEGER PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    path TEXT NOT NULL,
    unit_kind TEXT NOT NULL,
    unit_identity TEXT NOT NULL DEFAULT '',
    symbol_name TEXT,
    language TEXT,
    source_sha256 TEXT NOT NULL,
    representation_sha256 TEXT NOT NULL,
    representation TEXT NOT NULL,
    qualification_state TEXT NOT NULL,
    tag_ruleset TEXT,
    start_byte INTEGER,
    end_byte INTEGER,
    start_line INTEGER,
    start_column INTEGER,
    end_line INTEGER,
    end_column INTEGER,
    UNIQUE (source_repository, source_revision, path, unit_kind, unit_identity)
);
CREATE TABLE IF NOT EXISTS harvest_record_tags (
    record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (record_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_harvest_records_provenance
ON harvest_records(source_repository, source_revision);
CREATE INDEX IF NOT EXISTS idx_harvest_records_symbol_name
ON harvest_records(symbol_name);
CREATE INDEX IF NOT EXISTS idx_harvest_record_tags_tag
ON harvest_record_tags(tag);
"""

_MIGRATE_V1_TO_V2 = """
DROP INDEX IF EXISTS idx_harvest_records_provenance;
DROP INDEX IF EXISTS idx_harvest_record_tags_tag;
ALTER TABLE harvest_record_tags RENAME TO harvest_record_tags_v1;
ALTER TABLE harvest_records RENAME TO harvest_records_v1;
CREATE TABLE harvest_records (
    id INTEGER PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    path TEXT NOT NULL,
    unit_kind TEXT NOT NULL,
    unit_identity TEXT NOT NULL DEFAULT '',
    symbol_name TEXT,
    language TEXT,
    source_sha256 TEXT NOT NULL,
    representation_sha256 TEXT NOT NULL,
    representation TEXT NOT NULL,
    qualification_state TEXT NOT NULL,
    tag_ruleset TEXT,
    start_byte INTEGER,
    end_byte INTEGER,
    start_line INTEGER,
    start_column INTEGER,
    end_line INTEGER,
    end_column INTEGER,
    UNIQUE (source_repository, source_revision, path, unit_kind, unit_identity)
);
INSERT INTO harvest_records (
    id, source_repository, source_revision, path, unit_kind, unit_identity,
    symbol_name, language, source_sha256, representation_sha256, representation,
    qualification_state, tag_ruleset, start_byte, end_byte, start_line,
    start_column, end_line, end_column
)
SELECT
    id, source_repository, source_revision, path, unit_kind, '',
    NULL, language, source_sha256, representation_sha256, representation,
    qualification_state, tag_ruleset, NULL, NULL, NULL, NULL, NULL, NULL
FROM harvest_records_v1;
CREATE TABLE harvest_record_tags (
    record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (record_id, tag)
);
INSERT INTO harvest_record_tags(record_id, tag)
SELECT record_id, tag FROM harvest_record_tags_v1;
DROP TABLE harvest_record_tags_v1;
DROP TABLE harvest_records_v1;
CREATE INDEX idx_harvest_records_provenance
ON harvest_records(source_repository, source_revision);
CREATE INDEX idx_harvest_records_symbol_name
ON harvest_records(symbol_name);
CREATE INDEX idx_harvest_record_tags_tag
ON harvest_record_tags(tag);
PRAGMA user_version = 2;
"""

_RECORD_COLUMNS = """
r.id, r.source_repository, r.source_revision, r.path, r.unit_kind, r.unit_identity,
r.symbol_name, r.language, r.source_sha256, r.representation_sha256, r.representation,
r.qualification_state, r.tag_ruleset, r.start_byte, r.end_byte, r.start_line,
r.start_column, r.end_line, r.end_column
"""


class SQLiteHarvestStore:
    """Persist and exactly retrieve provenance-backed harvest records."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Create or migrate the versioned schema."""
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                connection.executescript(_SCHEMA_V2)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return
            if version == 1:
                connection.commit()
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.executescript(_MIGRATE_V1_TO_V2)
                connection.execute("PRAGMA foreign_keys = ON")
                return
            if version != SCHEMA_VERSION:
                message = f"unsupported RepoHarvester SQLite schema version: {version}"
                raise RuntimeError(message)
            connection.executescript(_SCHEMA_V2)

    def upsert_records(self, records: Iterable[HarvestRecord]) -> int:
        """Insert or replace record payloads while preserving stable source identity."""
        materialized = list(records)
        self.initialize()
        with self._connect() as connection:
            for record in materialized:
                connection.execute(
                    """
                    INSERT INTO harvest_records (
                        source_repository, source_revision, path, unit_kind, unit_identity,
                        symbol_name, language, source_sha256, representation_sha256,
                        representation, qualification_state, tag_ruleset, start_byte,
                        end_byte, start_line, start_column, end_line, end_column
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_repository, source_revision, path, unit_kind, unit_identity)
                    DO UPDATE SET
                        symbol_name = excluded.symbol_name,
                        language = excluded.language,
                        source_sha256 = excluded.source_sha256,
                        representation_sha256 = excluded.representation_sha256,
                        representation = excluded.representation,
                        qualification_state = excluded.qualification_state,
                        tag_ruleset = excluded.tag_ruleset,
                        start_byte = excluded.start_byte,
                        end_byte = excluded.end_byte,
                        start_line = excluded.start_line,
                        start_column = excluded.start_column,
                        end_line = excluded.end_line,
                        end_column = excluded.end_column
                    """,
                    (
                        record.source_repository,
                        record.source_revision,
                        record.path,
                        record.unit_kind,
                        record.unit_identity,
                        record.symbol_name,
                        record.language,
                        record.source_sha256,
                        record.representation_sha256,
                        record.representation,
                        record.qualification_state.value,
                        record.tag_ruleset,
                        record.start_byte,
                        record.end_byte,
                        record.start_line,
                        record.start_column,
                        record.end_line,
                        record.end_column,
                    ),
                )
                record_id = connection.execute(
                    """
                    SELECT id FROM harvest_records
                    WHERE source_repository = ? AND source_revision = ? AND path = ?
                      AND unit_kind = ? AND unit_identity = ?
                    """,
                    (
                        record.source_repository,
                        record.source_revision,
                        record.path,
                        record.unit_kind,
                        record.unit_identity,
                    ),
                ).fetchone()[0]
                connection.execute("DELETE FROM harvest_record_tags WHERE record_id = ?", (record_id,))
                connection.executemany(
                    "INSERT INTO harvest_record_tags(record_id, tag) VALUES (?, ?)",
                    ((record_id, tag) for tag in sorted(set(record.tags))),
                )
        return len(materialized)

    def all_records(self) -> list[HarvestRecord]:
        """Load all records in deterministic provenance/path order."""
        return self.query_records()

    def query_records(
        self,
        *,
        source_repository: str | None = None,
        source_revision: str | None = None,
        path: str | None = None,
        unit_kind: str | None = None,
        unit_identity: str | None = None,
        symbol_name: str | None = None,
        language: str | None = None,
        qualification_state: QualificationState | None = None,
        tags: Iterable[str] = (),
    ) -> list[HarvestRecord]:
        """Return records matching every supplied exact filter and tag."""
        self.initialize()
        clauses: list[str] = []
        parameters: list[str] = []
        exact_filters = (
            ("r.source_repository", source_repository),
            ("r.source_revision", source_revision),
            ("r.path", path),
            ("r.unit_kind", unit_kind),
            ("r.unit_identity", unit_identity),
            ("r.symbol_name", symbol_name),
            ("r.language", language),
        )
        for column, value in exact_filters:
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)

        if qualification_state is not None:
            clauses.append("r.qualification_state = ?")
            parameters.append(qualification_state.value)

        for tag in sorted(set(tags)):
            clauses.append(
                "EXISTS (SELECT 1 FROM harvest_record_tags t "
                "WHERE t.record_id = r.id AND t.tag = ?)"
            )
            parameters.append(tag)

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        statement = (
            f"SELECT {_RECORD_COLUMNS} FROM harvest_records r{where} "
            "ORDER BY r.source_repository, r.source_revision, r.path, r.unit_kind, r.unit_identity"
        )
        with self._connect() as connection:
            rows = connection.execute(statement, parameters).fetchall()
            return self._records_from_rows(connection, rows)

    def _records_from_rows(
        self,
        connection: sqlite3.Connection,
        rows: list[tuple],
    ) -> list[HarvestRecord]:
        record_ids = [row[0] for row in rows]
        tags_by_record: dict[int, tuple[str, ...]] = {}
        if record_ids:
            placeholders = ",".join("?" for _ in record_ids)
            tag_rows = connection.execute(
                f"SELECT record_id, tag FROM harvest_record_tags "
                f"WHERE record_id IN ({placeholders}) ORDER BY record_id, tag",
                record_ids,
            ).fetchall()
            for record_id, tag in tag_rows:
                tags_by_record.setdefault(record_id, ())
                tags_by_record[record_id] += (tag,)

        return [
            HarvestRecord(
                source_repository=row[1],
                source_revision=row[2],
                path=row[3],
                unit_kind=row[4],
                unit_identity=row[5],
                symbol_name=row[6],
                language=row[7],
                source_sha256=row[8],
                representation_sha256=row[9],
                representation=row[10],
                qualification_state=QualificationState(row[11]),
                tags=tags_by_record.get(row[0], ()),
                tag_ruleset=row[12],
                start_byte=row[13],
                end_byte=row[14],
                start_line=row[15],
                start_column=row[16],
                end_line=row[17],
                end_column=row[18],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
