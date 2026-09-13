#!/usr/bin/env python3
"""Query RepoHarvester's local DevOS runtime and record system feedback."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

try:
    from tools.build_knowledge_db import DEFAULT_DB, ROOT, build
    from tools.db_runtime import connect_runtime, runtime_health
except ModuleNotFoundError:
    from build_knowledge_db import DEFAULT_DB, ROOT, build
    from db_runtime import connect_runtime, runtime_health

LOCK_PATH = ROOT / "devos" / "governance-lock.json"

AUTHORITY_RANK = {
    "USER_LOCKED_AUTHORITY": 100,
    "RATIFIED_SYSTEM_AUTHORITY": 90,
    "ACCEPTED_ARTIFACT_EVIDENCE": 80,
    "REPEATED_ACCEPTED_EVIDENCE": 75,
    "OBSERVED_RUNTIME_EVIDENCE": 70,
    "SOURCE_BACKED_RESEARCH": 50,
    "CANDIDATE_INFERENCE": 30,
    "CONFLICTED": 10,
    "SUPERSEDED": 0,
    "REJECTED": -10,
}

FEEDBACK_CATEGORIES = {
    "retrieval_failure",
    "utilization_failure",
    "stale_projection",
    "scope_leak",
    "authority_conflict",
    "validator_gap",
    "test_gap",
    "workflow_friction",
    "other",
}

SEVERITIES = {"low", "medium", "high", "critical"}


def ensure_db(db_path: Path) -> None:
    if not db_path.exists():
        build(db_path)


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    ensure_db(db_path)
    return connect_runtime(db_path)


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def lock_status(lock: dict, today: date | None = None) -> dict:
    current = today or date.today()
    valid_through = date.fromisoformat(lock["valid_through"])
    expired = current > valid_through
    return {
        "expired": expired,
        "valid_through": valid_through.isoformat(),
        "normal_repo_work_external_fetch_required": bool(
            lock["normal_repo_work_external_fetch_required"]
        ),
        "normal_repo_work_blocked": False,
        "authority_sensitive_upstream_sync": (
            "required_when_material" if expired else "not_required_by_age"
        ),
        "review_flag_on_age_alone": bool(
            lock["staleness_behavior"]["review_flag_on_age_alone"]
        ),
    }


def tokenize_fts(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_-]+", query)
    if not tokens:
        raise ValueError("query must contain at least one searchable token")
    return " AND ".join(f'"{token}"' for token in tokens)


def query_claims(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> list[dict]:
    fts_query = tokenize_fts(query)
    rows = connection.execute(
        """
        SELECT
            c.claim_id,
            c.branch_key,
            c.statement,
            c.authority_class,
            c.lifecycle,
            c.status,
            c.support_count,
            c.independent_support_count,
            c.verified_at,
            c.valid_through,
            c.source_ref
        FROM governance_claims_fts f
        JOIN governance_claims c ON c.claim_id = f.claim_id
        WHERE governance_claims_fts MATCH ?
        LIMIT ?
        """,
        (fts_query, limit * 4),
    ).fetchall()

    results = [dict(row) for row in rows]
    results.sort(
        key=lambda row: (
            AUTHORITY_RANK.get(row["authority_class"], -100),
            row["independent_support_count"],
            row["support_count"],
            row["verified_at"],
        ),
        reverse=True,
    )
    for row in results:
        row["authority_rank"] = AUTHORITY_RANK.get(row["authority_class"], -100)
        row["prevalence"] = {
            "support_count": row.pop("support_count"),
            "independent_support_count": row.pop("independent_support_count"),
            "can_upgrade_authority": False,
        }
    return results[:limit]


def status_payload(connection: sqlite3.Connection) -> dict:
    meta = {
        row["key"]: row["value"]
        for row in connection.execute("SELECT key, value FROM governance_meta").fetchall()
    }
    return {
        "scope_key": meta.get("scope_key"),
        "snapshot_id": meta.get("snapshot_id"),
        "materialized_on": meta.get("materialized_on"),
        "source_repository_head": meta.get("source_repository_head"),
        "governance_claim_count": connection.execute(
            "SELECT count(*) FROM governance_claims"
        ).fetchone()[0],
        "branch_count": connection.execute(
            "SELECT count(*) FROM branch_state"
        ).fetchone()[0],
        "task_count": connection.execute(
            "SELECT count(*) FROM devos_tasks"
        ).fetchone()[0],
        "research_episode_count": connection.execute(
            "SELECT count(*) FROM research_episodes"
        ).fetchone()[0],
        "candidate_opportunity_count": connection.execute(
            "SELECT count(*) FROM research_opportunities WHERE status = 'CANDIDATE'"
        ).fetchone()[0],
        "feedback_event_count": connection.execute(
            "SELECT count(*) FROM system_feedback"
        ).fetchone()[0],
        "improvement_candidate_count": connection.execute(
            "SELECT count(*) FROM improvement_candidates"
        ).fetchone()[0],
        "learning": {
            "procedure_count": connection.execute(
                "SELECT count(*) FROM learning_procedures"
            ).fetchone()[0],
            "evaluation_count": connection.execute(
                "SELECT count(*) FROM learning_evaluations"
            ).fetchone()[0],
            "experience_count": connection.execute(
                "SELECT count(*) FROM learning_experiences"
            ).fetchone()[0],
            "capability_count": connection.execute(
                "SELECT count(*) FROM learning_capabilities"
            ).fetchone()[0],
            "capability_event_count": connection.execute(
                "SELECT count(*) FROM learning_capability_events"
            ).fetchone()[0],
        },
        "database": runtime_health(connection),
        "lock": lock_status(load_lock()),
    }


def record_feedback(
    connection: sqlite3.Connection,
    *,
    episode_id: str,
    branch_key: str,
    category: str,
    signature: str,
    summary: str,
    evidence_ref: str,
    severity: str,
    created_at: str | None = None,
) -> str:
    if category not in FEEDBACK_CATEGORIES:
        raise ValueError(
            f"category must be one of: {', '.join(sorted(FEEDBACK_CATEGORIES))}"
        )
    if severity not in SEVERITIES:
        raise ValueError(
            f"severity must be one of: {', '.join(sorted(SEVERITIES))}"
        )
    known_branch = connection.execute(
        "SELECT 1 FROM branch_state WHERE branch_key = ?",
        (branch_key,),
    ).fetchone()
    if not known_branch:
        raise ValueError(f"unknown branch_key: {branch_key}")

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    digest_input = "\0".join(
        [episode_id, branch_key, category, signature, evidence_ref, timestamp]
    )
    event_id = "feedback-" + hashlib.sha256(
        digest_input.encode("utf-8")
    ).hexdigest()[:16]

    connection.execute(
        """
        INSERT INTO system_feedback(
            event_id, episode_id, branch_key, category, signature, summary,
            evidence_ref, severity, disposition, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            event_id,
            episode_id,
            branch_key,
            category,
            signature,
            summary,
            evidence_ref,
            severity,
            timestamp,
        ),
    )
    connection.commit()
    return event_id


def list_candidates(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
            branch_key,
            category,
            signature,
            occurrence_count,
            independent_episode_count,
            first_seen,
            last_seen
        FROM improvement_candidates
        ORDER BY independent_episode_count DESC, occurrence_count DESC, last_seen DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    claims = subparsers.add_parser("claims")
    claims.add_argument("query")
    claims.add_argument("--limit", type=int, default=20)

    feedback = subparsers.add_parser("feedback")
    feedback.add_argument("--episode", required=True)
    feedback.add_argument("--branch", required=True)
    feedback.add_argument(
        "--category", required=True, choices=sorted(FEEDBACK_CATEGORIES)
    )
    feedback.add_argument("--signature", required=True)
    feedback.add_argument("--summary", required=True)
    feedback.add_argument("--evidence-ref", required=True)
    feedback.add_argument(
        "--severity", required=True, choices=sorted(SEVERITIES)
    )

    subparsers.add_parser("candidates")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connection: sqlite3.Connection | None = None
    try:
        connection = connect(args.db)
        if args.command == "status":
            print(json.dumps(status_payload(connection), indent=2, sort_keys=True))
        elif args.command == "claims":
            print(
                json.dumps(
                    query_claims(connection, args.query, limit=args.limit),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "feedback":
            event_id = record_feedback(
                connection,
                episode_id=args.episode,
                branch_key=args.branch,
                category=args.category,
                signature=args.signature,
                summary=args.summary,
                evidence_ref=args.evidence_ref,
                severity=args.severity,
            )
            print(event_id)
        elif args.command == "candidates":
            print(json.dumps(list_candidates(connection), indent=2, sort_keys=True))
        else:
            raise ValueError(f"unknown command: {args.command}")
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        print(f"knowledge runtime failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
