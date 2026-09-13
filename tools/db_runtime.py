#!/usr/bin/env python3
"""Shared SQLite runtime policy and schema migrations for RepoHarvester DevOS."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = ROOT / "knowledge" / "schema.sql"
CURRENT_SCHEMA_VERSION = 2
BUSY_TIMEOUT_MS = 5000
MIGRATION_2_SIGNATURE = "runtime-db-v2:learning+tasks+research+edges+chronology+indexes:v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    declaration: str,
) -> None:
    if column not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def _json_list(raw: str | None) -> list[object]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def _json_object(raw: str | None) -> dict[str, object]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _backfill_capability_chronology(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "learning_capability_events"):
        return
    capability_ids = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT capability_id FROM learning_capability_events ORDER BY capability_id"
        ).fetchall()
    ]
    for capability_id in capability_ids:
        rows = connection.execute(
            """
            SELECT rowid, event_id, event_sequence, created_at, predecessor_event_id
            FROM learning_capability_events
            WHERE capability_id = ?
            ORDER BY
                CASE WHEN event_sequence > 0 THEN 0 ELSE 1 END,
                event_sequence,
                CASE WHEN created_at <> '' THEN created_at ELSE '9999' END,
                rowid,
                event_id
            """,
            (capability_id,),
        ).fetchall()
        sequences = [int(row["event_sequence"]) for row in rows]
        valid = (
            all(sequence > 0 for sequence in sequences)
            and len(sequences) == len(set(sequences))
        )
        if valid:
            # Preserve already-versioned history, but repair missing predecessor links.
            previous = ""
            for row in sorted(rows, key=lambda item: int(item["event_sequence"])):
                if row["predecessor_event_id"] != previous:
                    connection.execute(
                        "UPDATE learning_capability_events SET predecessor_event_id = ? WHERE event_id = ?",
                        (previous, row["event_id"]),
                    )
                previous = row["event_id"]
            continue

        # Legacy events had no chronology. rowid is the best available local
        # insertion order, made explicit once during migration.
        legacy_rows = sorted(rows, key=lambda item: (int(item["rowid"]), item["event_id"]))
        previous = ""
        for sequence, row in enumerate(legacy_rows, 1):
            connection.execute(
                """
                UPDATE learning_capability_events
                SET event_sequence = ?,
                    predecessor_event_id = ?,
                    created_at = CASE WHEN created_at = '' THEN ? ELSE created_at END
                WHERE event_id = ?
                """,
                (
                    sequence,
                    previous,
                    "1970-01-01T00:00:00+00:00",
                    row["event_id"],
                ),
            )
            previous = row["event_id"]


def _backfill_learning_edges(connection: sqlite3.Connection) -> None:
    if _table_exists(connection, "learning_procedures"):
        for row in connection.execute(
            "SELECT procedure_id, payload_json FROM learning_procedures"
        ).fetchall():
            payload = _json_object(row["payload_json"])
            for ref in payload.get("source_evidence_refs", []) or []:
                connection.execute(
                    "INSERT OR IGNORE INTO procedure_evidence(procedure_id, evidence_ref) VALUES (?, ?)",
                    (row["procedure_id"], str(ref)),
                )

    if _table_exists(connection, "learning_experiences"):
        for row in connection.execute(
            "SELECT memory_id, source_evidence_refs_json FROM learning_experiences"
        ).fetchall():
            for ref in _json_list(row["source_evidence_refs_json"]):
                connection.execute(
                    "INSERT OR IGNORE INTO experience_evidence(memory_id, evidence_ref) VALUES (?, ?)",
                    (row["memory_id"], str(ref)),
                )

    if _table_exists(connection, "learning_capabilities"):
        for row in connection.execute(
            "SELECT capability_id, payload_json FROM learning_capabilities"
        ).fetchall():
            payload = _json_object(row["payload_json"])
            maturity = str(payload.get("maturity_stage") or "RECALL")
            connection.execute(
                "UPDATE learning_capabilities SET maturity_stage = ? WHERE capability_id = ?",
                (maturity, row["capability_id"]),
            )
            for ordinal, procedure_id in enumerate(payload.get("procedure_ids", []) or []):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO capability_procedures(
                        capability_id, procedure_id, ordinal
                    ) VALUES (?, ?, ?)
                    """,
                    (row["capability_id"], str(procedure_id), ordinal),
                )
            for ordinal, fixture_id in enumerate(
                payload.get("transfer_fixture_ids", []) or []
            ):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO capability_transfer_fixtures(
                        capability_id, fixture_id, ordinal
                    ) VALUES (?, ?, ?)
                    """,
                    (row["capability_id"], str(fixture_id), ordinal),
                )


def _backfill_finding_edges(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "atomic_findings"):
        return
    rows = connection.execute(
        "SELECT finding_id, root_ids_json FROM atomic_findings"
    ).fetchall()
    for row in rows:
        for ordinal, root_id in enumerate(_json_list(row["root_ids_json"])):
            connection.execute(
                """
                INSERT OR IGNORE INTO finding_roots(finding_id, root_id, ordinal)
                VALUES (?, ?, ?)
                """,
                (row["finding_id"], str(root_id), ordinal),
            )


def _migration_2(connection: sqlite3.Connection) -> None:
    """Unify learning/task/research persistence and normalize hot relationships."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS learning_procedures (
            procedure_id TEXT PRIMARY KEY,
            branch_scope TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS learning_evaluations (
            evaluation_id TEXT PRIMARY KEY,
            procedure_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT '',
            evaluator_version TEXT NOT NULL DEFAULT 'learning-threshold:v1'
        );

        CREATE TABLE IF NOT EXISTS learning_experiences (
            memory_id TEXT PRIMARY KEY,
            memory_type TEXT NOT NULL,
            branch_scope TEXT NOT NULL,
            statement TEXT NOT NULL,
            source_evidence_refs_json TEXT NOT NULL,
            procedure_id TEXT NOT NULL,
            capability_id TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS learning_capabilities (
            capability_id TEXT PRIMARY KEY,
            branch_scope TEXT NOT NULL,
            maturity_stage TEXT NOT NULL DEFAULT 'RECALL',
            payload_json TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS learning_capability_events (
            event_id TEXT PRIMARY KEY,
            capability_id TEXT NOT NULL,
            branch_scope TEXT NOT NULL,
            maturity_stage TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT '',
            event_sequence INTEGER NOT NULL DEFAULT 0,
            episode_id TEXT NOT NULL DEFAULT '',
            predecessor_event_id TEXT NOT NULL DEFAULT '',
            evaluator_version TEXT NOT NULL DEFAULT 'learning-threshold:v1'
        );

        CREATE TABLE IF NOT EXISTS procedure_evidence (
            procedure_id TEXT NOT NULL,
            evidence_ref TEXT NOT NULL,
            PRIMARY KEY(procedure_id, evidence_ref),
            FOREIGN KEY(procedure_id) REFERENCES learning_procedures(procedure_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experience_evidence (
            memory_id TEXT NOT NULL,
            evidence_ref TEXT NOT NULL,
            PRIMARY KEY(memory_id, evidence_ref),
            FOREIGN KEY(memory_id) REFERENCES learning_experiences(memory_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS capability_procedures (
            capability_id TEXT NOT NULL,
            procedure_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(capability_id, procedure_id),
            FOREIGN KEY(capability_id) REFERENCES learning_capabilities(capability_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS capability_transfer_fixtures (
            capability_id TEXT NOT NULL,
            fixture_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(capability_id, fixture_id),
            FOREIGN KEY(capability_id) REFERENCES learning_capabilities(capability_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finding_roots (
            finding_id TEXT NOT NULL,
            root_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(finding_id, root_id),
            FOREIGN KEY(finding_id) REFERENCES atomic_findings(finding_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS devos_tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL,
            task_type TEXT NOT NULL,
            owner_role TEXT NOT NULL,
            assigned_agent TEXT,
            objective TEXT NOT NULL,
            transfer_canary INTEGER NOT NULL,
            tracking_json TEXT NOT NULL,
            acceptance_json TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL,
            manifest_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS task_branches (
            task_id TEXT NOT NULL,
            branch_key TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(task_id, branch_key),
            FOREIGN KEY(task_id) REFERENCES devos_tasks(task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id TEXT NOT NULL,
            depends_on_task_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(task_id, depends_on_task_id),
            FOREIGN KEY(task_id) REFERENCES devos_tasks(task_id) ON DELETE CASCADE,
            FOREIGN KEY(depends_on_task_id) REFERENCES devos_tasks(task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS research_opportunities (
            opportunity_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            need TEXT NOT NULL,
            proposal TEXT NOT NULL,
            expected_value TEXT NOT NULL,
            novelty_reason TEXT NOT NULL,
            project_fit TEXT NOT NULL,
            risks_json TEXT NOT NULL,
            validation_plan_json TEXT NOT NULL,
            cross_reference_disposition TEXT NOT NULL,
            suggested_disposition TEXT NOT NULL,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            manifest_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS opportunity_branches (
            opportunity_id TEXT NOT NULL,
            branch_key TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(opportunity_id, branch_key),
            FOREIGN KEY(opportunity_id) REFERENCES research_opportunities(opportunity_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS opportunity_tasks (
            opportunity_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(opportunity_id, task_id),
            FOREIGN KEY(opportunity_id) REFERENCES research_opportunities(opportunity_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS opportunity_sources (
            opportunity_id TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(opportunity_id, source_ref, source_kind),
            FOREIGN KEY(opportunity_id) REFERENCES research_opportunities(opportunity_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS research_episodes (
            research_id TEXT PRIMARY KEY,
            trigger_signals_json TEXT NOT NULL,
            questions_json TEXT NOT NULL,
            queries_json TEXT NOT NULL,
            claims_json TEXT NOT NULL,
            uncertainties_json TEXT NOT NULL,
            inspirations_json TEXT NOT NULL,
            opportunities_json TEXT NOT NULL,
            no_op_reason TEXT,
            authority_effect TEXT NOT NULL,
            promotion_state TEXT NOT NULL,
            receipt_path TEXT NOT NULL,
            receipt_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS research_episode_tasks (
            research_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(research_id, task_id),
            FOREIGN KEY(research_id) REFERENCES research_episodes(research_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS research_episode_branches (
            research_id TEXT NOT NULL,
            branch_key TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(research_id, branch_key),
            FOREIGN KEY(research_id) REFERENCES research_episodes(research_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS research_sources (
            research_id TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            source_class TEXT NOT NULL,
            title TEXT NOT NULL,
            published_or_updated TEXT,
            retrieved_on TEXT NOT NULL,
            ordinal INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(research_id, source_ref),
            FOREIGN KEY(research_id) REFERENCES research_episodes(research_id) ON DELETE CASCADE
        );
        """
    )

    # Upgrade databases created by the pre-v2 standalone LearningStore.
    if _table_exists(connection, "learning_procedures"):
        _ensure_column(connection, "learning_procedures", "created_at", "TEXT NOT NULL DEFAULT ''")
    if _table_exists(connection, "learning_evaluations"):
        _ensure_column(connection, "learning_evaluations", "created_at", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(
            connection,
            "learning_evaluations",
            "evaluator_version",
            "TEXT NOT NULL DEFAULT 'learning-threshold:v1'",
        )
    if _table_exists(connection, "learning_experiences"):
        _ensure_column(connection, "learning_experiences", "created_at", "TEXT NOT NULL DEFAULT ''")
    if _table_exists(connection, "learning_capabilities"):
        _ensure_column(connection, "learning_capabilities", "maturity_stage", "TEXT NOT NULL DEFAULT 'RECALL'")
        _ensure_column(connection, "learning_capabilities", "updated_at", "TEXT NOT NULL DEFAULT ''")
    if _table_exists(connection, "learning_capability_events"):
        _ensure_column(connection, "learning_capability_events", "created_at", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "learning_capability_events", "event_sequence", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "learning_capability_events", "episode_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "learning_capability_events", "predecessor_event_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(
            connection,
            "learning_capability_events",
            "evaluator_version",
            "TEXT NOT NULL DEFAULT 'learning-threshold:v1'",
        )

    _backfill_capability_chronology(connection)
    _backfill_learning_edges(connection)
    _backfill_finding_edges(connection)

    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_learning_procedures_branch
            ON learning_procedures(branch_scope);
        CREATE INDEX IF NOT EXISTS idx_learning_evaluations_procedure
            ON learning_evaluations(procedure_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_learning_experiences_branch_type
            ON learning_experiences(branch_scope, memory_type);
        CREATE INDEX IF NOT EXISTS idx_learning_experiences_procedure
            ON learning_experiences(procedure_id) WHERE procedure_id <> '';
        CREATE INDEX IF NOT EXISTS idx_learning_experiences_capability
            ON learning_experiences(capability_id) WHERE capability_id <> '';
        CREATE INDEX IF NOT EXISTS idx_learning_capabilities_branch_maturity
            ON learning_capabilities(branch_scope, maturity_stage);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_capability_event_sequence
            ON learning_capability_events(capability_id, event_sequence);
        CREATE INDEX IF NOT EXISTS idx_capability_event_created
            ON learning_capability_events(capability_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_procedure_evidence_ref
            ON procedure_evidence(evidence_ref);
        CREATE INDEX IF NOT EXISTS idx_experience_evidence_ref
            ON experience_evidence(evidence_ref);
        CREATE INDEX IF NOT EXISTS idx_finding_roots_root
            ON finding_roots(root_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
            ON devos_tasks(status, priority, task_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_ready
            ON devos_tasks(priority, task_id)
            WHERE status = 'READY' AND assigned_agent IS NULL;
        CREATE INDEX IF NOT EXISTS idx_task_dependencies_dep
            ON task_dependencies(depends_on_task_id);
        CREATE INDEX IF NOT EXISTS idx_task_branches_branch
            ON task_branches(branch_key, task_id);
        CREATE INDEX IF NOT EXISTS idx_opportunities_status
            ON research_opportunities(status, opportunity_id);
        CREATE INDEX IF NOT EXISTS idx_opportunities_candidate
            ON research_opportunities(opportunity_id)
            WHERE status = 'CANDIDATE';
        CREATE INDEX IF NOT EXISTS idx_opportunity_tasks_task
            ON opportunity_tasks(task_id, opportunity_id);
        CREATE INDEX IF NOT EXISTS idx_research_episode_tasks_task
            ON research_episode_tasks(task_id, research_id);
        CREATE INDEX IF NOT EXISTS idx_research_episode_branches_branch
            ON research_episode_branches(branch_key, research_id);
        CREATE INDEX IF NOT EXISTS idx_research_sources_ref
            ON research_sources(source_ref, research_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_open
            ON system_feedback(branch_key, category, signature, created_at)
            WHERE disposition = 'open';
        """
    )


def _record_migration(
    connection: sqlite3.Connection,
    version: int,
    name: str,
    checksum: str,
) -> None:
    existing = connection.execute(
        "SELECT name, checksum FROM schema_migrations WHERE version = ?",
        (version,),
    ).fetchone()
    if existing is not None:
        if existing["name"] != name or existing["checksum"] != checksum:
            raise RuntimeError(
                f"schema migration {version} checksum/name mismatch: "
                f"database={existing['name']}:{existing['checksum']} "
                f"runtime={name}:{checksum}"
            )
        return
    connection.execute(
        """
        INSERT INTO schema_migrations(version, name, checksum, applied_at)
        VALUES (?, ?, ?, ?)
        """,
        (version, name, checksum, _utc_now()),
    )


def initialize_runtime(connection: sqlite3.Connection) -> None:
    """Install the frozen v1 baseline and apply deterministic migrations."""
    baseline = BASE_SCHEMA.read_text(encoding="utf-8")
    connection.executescript(baseline)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    _record_migration(
        connection,
        1,
        "baseline-knowledge-runtime",
        _sha256(baseline),
    )

    v2_checksum = _sha256(MIGRATION_2_SIGNATURE)
    existing_v2 = connection.execute(
        "SELECT 1 FROM schema_migrations WHERE version = 2"
    ).fetchone()
    _migration_2(connection)
    if existing_v2 is None:
        _record_migration(connection, 2, "runtime-db-v2", v2_checksum)
    else:
        _record_migration(connection, 2, "runtime-db-v2", v2_checksum)

    connection.execute(f"PRAGMA user_version={CURRENT_SCHEMA_VERSION}")
    connection.execute("PRAGMA optimize")
    connection.commit()


def connect_runtime(
    db_path: str | Path,
    *,
    initialize: bool = True,
    timeout_seconds: float = 5.0,
) -> sqlite3.Connection:
    """Open a DevOS SQLite connection with one shared local-runtime policy."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=timeout_seconds)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    # WAL is persistent for file databases; :memory: reports journal_mode=memory.
    connection.execute("PRAGMA journal_mode=WAL").fetchone()
    connection.execute("PRAGMA synchronous=NORMAL")
    if initialize:
        initialize_runtime(connection)
    return connection


def runtime_health(connection: sqlite3.Connection) -> dict[str, object]:
    migration = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]
    return {
        "schema_version": int(migration),
        "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
        "sqlite_version": sqlite3.sqlite_version,
        "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
        "foreign_keys": bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
        "busy_timeout_ms": connection.execute("PRAGMA busy_timeout").fetchone()[0],
        "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
    }


def cleanup_runtime_files(db_path: str | Path) -> None:
    path = Path(db_path)
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        candidate.unlink(missing_ok=True)
