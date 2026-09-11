"""Deterministic SQLite persistence for harvest records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from repoharvester.models import HarvestRecord, QualificationState

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS harvest_records (
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
CREATE TABLE IF NOT EXISTS harvest_record_tags (
    record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (record_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_harvest_records_provenance
ON harvest_records(source_repository, source_revision);
CREATE INDEX IF NOT EXISTS idx_harvest_record_tags_tag
ON harvest_record_tags(tag);
"""


class SQLiteHarvestStore:
    """Persist provenance-backed harvest records in one local SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Create the versioned schema if it does not already exist."""
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def upsert_records(self, records: Iterable[HarvestRecord]) -> int:
        """Insert or replace record payloads while preserving stable source identity."""
        materialized = list(records)
        self.initialize()
        with self._connect() as connection:
            for record in materialized:
                connection.execute(
                    """
                    INSERT INTO harvest_records (
                        source_repository, source_revision, path, unit_kind, language,
                        source_sha256, representation_sha256, representation,
                        qualification_state, tag_ruleset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_repository, source_revision, path, unit_kind)
                    DO UPDATE SET
                        language = excluded.language,
                        source_sha256 = excluded.source_sha256,
                        representation_sha256 = excluded.representation_sha256,
                        representation = excluded.representation,
                        qualification_state = excluded.qualification_state,
                        tag_ruleset = excluded.tag_ruleset
                    """,
                    (
                        record.source_repository,
                        record.source_revision,
                        record.path,
                        record.unit_kind,
                        record.language,
                        record.source_sha256,
                        record.representation_sha256,
                        record.representation,
                        record.qualification_state.value,
                        record.tag_ruleset,
                    ),
                )
                record_id = connection.execute(
                    """
                    SELECT id FROM harvest_records
                    WHERE source_repository = ? AND source_revision = ? AND path = ? AND unit_kind = ?
                    """,
                    (record.source_repository, record.source_revision, record.path, record.unit_kind),
                ).fetchone()[0]
                connection.execute("DELETE FROM harvest_record_tags WHERE record_id = ?", (record_id,))
                connection.executemany(
                    "INSERT INTO harvest_record_tags(record_id, tag) VALUES (?, ?)",
                    ((record_id, tag) for tag in sorted(set(record.tags))),
                )
        return len(materialized)

    def all_records(self) -> list[HarvestRecord]:
        """Load all records in deterministic provenance/path order."""
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, source_repository, source_revision, path, unit_kind, language,
                       source_sha256, representation_sha256, representation,
                       qualification_state, tag_ruleset
                FROM harvest_records
                ORDER BY source_repository, source_revision, path, unit_kind
                """
            ).fetchall()
            tags_by_record: dict[int, tuple[str, ...]] = {}
            for row in connection.execute(
                "SELECT record_id, tag FROM harvest_record_tags ORDER BY record_id, tag"
            ).fetchall():
                tags_by_record.setdefault(row[0], ())
                tags_by_record[row[0]] += (row[1],)

        return [
            HarvestRecord(
                source_repository=row[1],
                source_revision=row[2],
                path=row[3],
                unit_kind=row[4],
                language=row[5],
                source_sha256=row[6],
                representation_sha256=row[7],
                representation=row[8],
                qualification_state=QualificationState(row[9]),
                tags=tags_by_record.get(row[0], ()),
                tag_ruleset=row[10],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
