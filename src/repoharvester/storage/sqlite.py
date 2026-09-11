"""Deterministic SQLite persistence and exact retrieval for harvest evidence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from repoharvester.models import (
    HarvestRecord,
    HarvestRelationship,
    QualificationState,
    ResolutionState,
)

SCHEMA_VERSION = 3

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS harvest_records (
    id INTEGER PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    path TEXT NOT NULL,
    unit_kind TEXT NOT NULL,
    unit_identity TEXT NOT NULL DEFAULT '',
    language TEXT,
    source_sha256 TEXT NOT NULL,
    representation_sha256 TEXT NOT NULL,
    representation TEXT NOT NULL,
    qualification_state TEXT NOT NULL,
    tag_ruleset TEXT,
    symbol_name TEXT,
    start_byte INTEGER,
    end_byte INTEGER,
    start_row INTEGER,
    start_column INTEGER,
    end_row INTEGER,
    end_column INTEGER,
    UNIQUE (source_repository, source_revision, path, unit_kind, unit_identity)
);
CREATE TABLE IF NOT EXISTS harvest_record_tags (
    record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (record_id, tag)
);
CREATE TABLE IF NOT EXISTS harvest_relationships (
    id INTEGER PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_unit_kind TEXT NOT NULL,
    source_unit_identity TEXT NOT NULL DEFAULT '',
    relationship_kind TEXT NOT NULL,
    target_path TEXT NOT NULL DEFAULT '',
    target_unit_kind TEXT NOT NULL DEFAULT '',
    target_unit_identity TEXT NOT NULL DEFAULT '',
    literal_target TEXT NOT NULL DEFAULT '',
    resolution_state TEXT NOT NULL,
    start_byte INTEGER,
    end_byte INTEGER,
    start_row INTEGER,
    start_column INTEGER,
    end_row INTEGER,
    end_column INTEGER,
    extractor_name TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    UNIQUE (
        source_repository, source_revision, source_path, source_unit_kind,
        source_unit_identity, relationship_kind, target_path, target_unit_kind,
        target_unit_identity, literal_target, start_byte, end_byte
    )
);
CREATE INDEX IF NOT EXISTS idx_harvest_records_provenance
ON harvest_records(source_repository, source_revision);
CREATE INDEX IF NOT EXISTS idx_harvest_records_symbol
ON harvest_records(source_repository, source_revision, path, symbol_name);
CREATE INDEX IF NOT EXISTS idx_harvest_record_tags_tag
ON harvest_record_tags(tag);
CREATE INDEX IF NOT EXISTS idx_harvest_relationships_source
ON harvest_relationships(source_repository, source_revision, source_path, relationship_kind);
CREATE INDEX IF NOT EXISTS idx_harvest_relationships_target
ON harvest_relationships(source_repository, source_revision, target_path, target_unit_identity);
"""

_MIGRATE_V1_TO_V2 = """
ALTER TABLE harvest_record_tags RENAME TO harvest_record_tags_v1;
ALTER TABLE harvest_records RENAME TO harvest_records_v1;
CREATE TABLE harvest_records (
    id INTEGER PRIMARY KEY,
    source_repository TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    path TEXT NOT NULL,
    unit_kind TEXT NOT NULL,
    unit_identity TEXT NOT NULL DEFAULT '',
    language TEXT,
    source_sha256 TEXT NOT NULL,
    representation_sha256 TEXT NOT NULL,
    representation TEXT NOT NULL,
    qualification_state TEXT NOT NULL,
    tag_ruleset TEXT,
    symbol_name TEXT,
    start_byte INTEGER,
    end_byte INTEGER,
    start_row INTEGER,
    start_column INTEGER,
    end_row INTEGER,
    end_column INTEGER,
    UNIQUE (source_repository, source_revision, path, unit_kind, unit_identity)
);
CREATE TABLE harvest_record_tags (
    record_id INTEGER NOT NULL REFERENCES harvest_records(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (record_id, tag)
);
INSERT INTO harvest_records (
    id, source_repository, source_revision, path, unit_kind, unit_identity, language,
    source_sha256, representation_sha256, representation, qualification_state, tag_ruleset
)
SELECT
    id, source_repository, source_revision, path, unit_kind, '', language,
    source_sha256, representation_sha256, representation, qualification_state, tag_ruleset
FROM harvest_records_v1;
INSERT INTO harvest_record_tags(record_id, tag)
SELECT record_id, tag FROM harvest_record_tags_v1;
DROP TABLE harvest_record_tags_v1;
DROP TABLE harvest_records_v1;
"""

_RECORD_COLUMNS = """
r.id, r.source_repository, r.source_revision, r.path, r.unit_kind, r.unit_identity, r.language,
r.source_sha256, r.representation_sha256, r.representation,
r.qualification_state, r.tag_ruleset, r.symbol_name,
r.start_byte, r.end_byte, r.start_row, r.start_column, r.end_row, r.end_column
"""

_RELATIONSHIP_COLUMNS = """
r.source_repository, r.source_revision, r.source_path, r.source_unit_kind,
r.source_unit_identity, r.relationship_kind, r.target_path, r.target_unit_kind,
r.target_unit_identity, r.literal_target, r.resolution_state,
r.start_byte, r.end_byte, r.start_row, r.start_column, r.end_row, r.end_column,
r.extractor_name, r.extractor_version
"""


class SQLiteHarvestStore:
    """Persist and exactly retrieve provenance-backed harvest evidence."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Create or migrate the compact local schema deterministically."""
        with sqlite3.connect(self.path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                connection.executescript(_SCHEMA)
            elif version == 1:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.executescript(_MIGRATE_V1_TO_V2)
                connection.executescript(_SCHEMA)
                connection.execute("PRAGMA foreign_keys = ON")
            elif version == 2:
                connection.executescript(_SCHEMA)
            elif version != SCHEMA_VERSION:
                message = f"unsupported harvest database schema version: {version}"
                raise RuntimeError(message)
            else:
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
                        source_repository, source_revision, path, unit_kind, unit_identity, language,
                        source_sha256, representation_sha256, representation,
                        qualification_state, tag_ruleset, symbol_name,
                        start_byte, end_byte, start_row, start_column, end_row, end_column
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_repository, source_revision, path, unit_kind, unit_identity)
                    DO UPDATE SET
                        language = excluded.language,
                        source_sha256 = excluded.source_sha256,
                        representation_sha256 = excluded.representation_sha256,
                        representation = excluded.representation,
                        qualification_state = excluded.qualification_state,
                        tag_ruleset = excluded.tag_ruleset,
                        symbol_name = excluded.symbol_name,
                        start_byte = excluded.start_byte,
                        end_byte = excluded.end_byte,
                        start_row = excluded.start_row,
                        start_column = excluded.start_column,
                        end_row = excluded.end_row,
                        end_column = excluded.end_column
                    """,
                    (
                        record.source_repository, record.source_revision, record.path, record.unit_kind,
                        record.unit_identity, record.language, record.source_sha256,
                        record.representation_sha256, record.representation,
                        record.qualification_state.value, record.tag_ruleset, record.symbol_name,
                        record.start_byte, record.end_byte, record.start_row, record.start_column,
                        record.end_row, record.end_column,
                    ),
                )
                record_id = connection.execute(
                    """
                    SELECT id FROM harvest_records
                    WHERE source_repository = ? AND source_revision = ? AND path = ?
                      AND unit_kind = ? AND unit_identity = ?
                    """,
                    (record.source_repository, record.source_revision, record.path,
                     record.unit_kind, record.unit_identity),
                ).fetchone()[0]
                connection.execute("DELETE FROM harvest_record_tags WHERE record_id = ?", (record_id,))
                connection.executemany(
                    "INSERT INTO harvest_record_tags(record_id, tag) VALUES (?, ?)",
                    ((record_id, tag) for tag in sorted(set(record.tags))),
                )
        return len(materialized)

    def upsert_relationships(self, relationships: Iterable[HarvestRelationship]) -> int:
        """Insert deterministic relationship evidence idempotently."""
        materialized = list(relationships)
        self.initialize()
        with self._connect() as connection:
            for relationship in materialized:
                connection.execute(
                    """
                    INSERT INTO harvest_relationships (
                        source_repository, source_revision, source_path, source_unit_kind,
                        source_unit_identity, relationship_kind, target_path, target_unit_kind,
                        target_unit_identity, literal_target, resolution_state,
                        start_byte, end_byte, start_row, start_column, end_row, end_column,
                        extractor_name, extractor_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO UPDATE SET
                        resolution_state = excluded.resolution_state,
                        start_row = excluded.start_row,
                        start_column = excluded.start_column,
                        end_row = excluded.end_row,
                        end_column = excluded.end_column,
                        extractor_name = excluded.extractor_name,
                        extractor_version = excluded.extractor_version
                    """,
                    (
                        relationship.source_repository, relationship.source_revision,
                        relationship.source_path, relationship.source_unit_kind,
                        relationship.source_unit_identity, relationship.relationship_kind,
                        relationship.target_path, relationship.target_unit_kind,
                        relationship.target_unit_identity, relationship.literal_target,
                        relationship.resolution_state.value, relationship.start_byte,
                        relationship.end_byte, relationship.start_row, relationship.start_column,
                        relationship.end_row, relationship.end_column,
                        relationship.extractor_name, relationship.extractor_version,
                    ),
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
            ("r.source_repository", source_repository), ("r.source_revision", source_revision),
            ("r.path", path), ("r.unit_kind", unit_kind), ("r.unit_identity", unit_identity),
            ("r.symbol_name", symbol_name), ("r.language", language),
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
                "EXISTS (SELECT 1 FROM harvest_record_tags t WHERE t.record_id = r.id AND t.tag = ?)"
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

    def query_relationships(
        self,
        *,
        source_repository: str | None = None,
        source_revision: str | None = None,
        source_path: str | None = None,
        relationship_kind: str | None = None,
        source_unit_identity: str | None = None,
        target_path: str | None = None,
        target_unit_identity: str | None = None,
        literal_target: str | None = None,
        resolution_state: ResolutionState | None = None,
    ) -> list[HarvestRelationship]:
        """Return relationships matching every supplied exact filter."""
        self.initialize()
        clauses: list[str] = []
        parameters: list[str] = []
        exact_filters = (
            ("r.source_repository", source_repository), ("r.source_revision", source_revision),
            ("r.source_path", source_path), ("r.relationship_kind", relationship_kind),
            ("r.source_unit_identity", source_unit_identity), ("r.target_path", target_path),
            ("r.target_unit_identity", target_unit_identity), ("r.literal_target", literal_target),
        )
        for column, value in exact_filters:
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        if resolution_state is not None:
            clauses.append("r.resolution_state = ?")
            parameters.append(resolution_state.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        statement = (
            f"SELECT {_RELATIONSHIP_COLUMNS} FROM harvest_relationships r{where} "
            "ORDER BY r.source_repository, r.source_revision, r.source_path, r.relationship_kind, "
            "r.target_path, r.target_unit_identity, r.literal_target, r.start_byte, r.end_byte"
        )
        with self._connect() as connection:
            rows = connection.execute(statement, parameters).fetchall()
        return [
            HarvestRelationship(
                source_repository=row[0], source_revision=row[1], source_path=row[2],
                source_unit_kind=row[3], source_unit_identity=row[4], relationship_kind=row[5],
                target_path=row[6], target_unit_kind=row[7], target_unit_identity=row[8],
                literal_target=row[9], resolution_state=ResolutionState(row[10]),
                start_byte=row[11], end_byte=row[12], start_row=row[13], start_column=row[14],
                end_row=row[15], end_column=row[16], extractor_name=row[17], extractor_version=row[18],
            )
            for row in rows
        ]

    def _records_from_rows(self, connection: sqlite3.Connection, rows: list[tuple]) -> list[HarvestRecord]:
        record_ids = [row[0] for row in rows]
        tags_by_record: dict[int, tuple[str, ...]] = {}
        if record_ids:
            placeholders = ",".join("?" for _ in record_ids)
            tag_rows = connection.execute(
                f"SELECT record_id, tag FROM harvest_record_tags WHERE record_id IN ({placeholders}) "
                "ORDER BY record_id, tag",
                record_ids,
            ).fetchall()
            for record_id, tag in tag_rows:
                tags_by_record.setdefault(record_id, ())
                tags_by_record[record_id] += (tag,)
        return [
            HarvestRecord(
                source_repository=row[1], source_revision=row[2], path=row[3], unit_kind=row[4],
                unit_identity=row[5], language=row[6], source_sha256=row[7],
                representation_sha256=row[8], representation=row[9],
                qualification_state=QualificationState(row[10]), tags=tags_by_record.get(row[0], ()),
                tag_ruleset=row[11], symbol_name=row[12], start_byte=row[13], end_byte=row[14],
                start_row=row[15], start_column=row[16], end_row=row[17], end_column=row[18],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
