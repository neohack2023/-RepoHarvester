#!/usr/bin/env python3
"""Persist and evaluate local DevOS evidence episodes."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

try:
    from tools.build_knowledge_db import DEFAULT_DB, build
    from tools.db_runtime import connect_runtime
    from tools.evidence_runtime import (
        AtomicFinding,
        CurrentClaim,
        LineageState,
        build_delta_packet,
        cross_reference,
        triangulate,
    )
except ModuleNotFoundError:
    from build_knowledge_db import DEFAULT_DB, build
    from db_runtime import connect_runtime
    from evidence_runtime import (
        AtomicFinding,
        CurrentClaim,
        LineageState,
        build_delta_packet,
        cross_reference,
        triangulate,
    )


def _id(prefix: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return prefix + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _claims(rows: list[dict]) -> dict[str, CurrentClaim]:
    return {
        r["claim_key"]: CurrentClaim(
            r["claim_id"], r["claim_key"], r["value"], r.get("lifecycle", "active")
        )
        for r in rows
    }


def _finding(row: dict) -> AtomicFinding:
    return AtomicFinding(
        finding_id=row["finding_id"],
        claim_key=row["claim_key"],
        value=row["value"],
        evidence_ref=row["evidence_ref"],
        root_ids=tuple(row.get("root_ids", [])),
        lineage_state=LineageState(row.get("lineage_state", "UNKNOWN_LINEAGE")),
        shared_input_keys=tuple(row.get("shared_input_keys", [])),
        related_claim_keys=tuple(row.get("related_claim_keys", [])),
        supersedes_claim_id=row.get("supersedes_claim_id"),
    )


def persist_episode(connection: sqlite3.Connection, episode: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    claims = _claims(episode["current_claims"])
    findings = [_finding(row) for row in episode["findings"]]

    for root in episode.get("roots", []):
        connection.execute(
            "INSERT OR REPLACE INTO evidence_roots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                root["root_id"],
                root["root_kind"],
                root["observation_question"],
                root.get("input_identity", ""),
                root.get("execution_identity", ""),
                root.get("source_revision", ""),
                root.get("environment_identity", ""),
                json.dumps(root.get("provenance_refs", []), sort_keys=True),
                now,
            ),
        )

    assessments = []
    for finding in findings:
        connection.execute(
            "INSERT OR REPLACE INTO atomic_findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding.finding_id,
                episode["episode_id"],
                episode["branch_key"],
                finding.claim_key,
                finding.value,
                finding.evidence_ref,
                json.dumps(finding.root_ids),
                finding.lineage_state.value,
                json.dumps(finding.shared_input_keys),
                json.dumps(finding.related_claim_keys),
                finding.supersedes_claim_id,
                now,
            ),
        )
        connection.execute(
            "DELETE FROM finding_roots WHERE finding_id = ?",
            (finding.finding_id,),
        )
        connection.executemany(
            "INSERT INTO finding_roots(finding_id, root_id, ordinal) VALUES (?, ?, ?)",
            (
                (finding.finding_id, root_id, ordinal)
                for ordinal, root_id in enumerate(finding.root_ids)
            ),
        )

        assessment = cross_reference(finding, claims)
        assessments.append(assessment)
        payload = {
            "finding_id": finding.finding_id,
            "cross_reference": assessment.cross_reference.value,
            "current_claim_id": assessment.current_claim_id,
        }
        connection.execute(
            "INSERT OR REPLACE INTO finding_assessments VALUES (?, ?, ?, ?, ?)",
            (
                _id("assessment-", payload),
                finding.finding_id,
                assessment.cross_reference.value,
                assessment.current_claim_id,
                now,
            ),
        )

    tri = triangulate(assessments, claim_key=episode["claim_key"])
    tri_data = {
        "claim_key": tri.claim_key,
        "state": tri.state.value,
        "root_summary": asdict(tri.root_summary),
        "supporting": tri.supporting_root_ids,
        "contradicting": tri.contradicting_root_ids,
        "notes": tri.notes,
    }
    batch_id = _id("tri-", {"episode_id": episode["episode_id"], **tri_data})
    connection.execute(
        "INSERT OR REPLACE INTO triangulation_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            batch_id,
            tri.claim_key,
            tri.state.value,
            json.dumps(asdict(tri.root_summary), sort_keys=True),
            json.dumps(tri.supporting_root_ids),
            json.dumps(tri.contradicting_root_ids),
            json.dumps(tri.notes),
            now,
        ),
    )

    delta = build_delta_packet(assessments, tri, claims)
    delta_json = json.dumps(asdict(delta), sort_keys=True)
    connection.execute(
        "INSERT OR REPLACE INTO evidence_delta_packets VALUES (?, ?, ?, ?)",
        (delta.delta_id, delta.claim_key, delta_json, now),
    )
    connection.commit()
    return {
        "episode_id": episode["episode_id"],
        "batch_id": batch_id,
        "triangulation_state": tri.state.value,
        "delta": asdict(delta),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        if not args.db.exists():
            build(args.db)
        episode = json.loads(args.input.read_text(encoding="utf-8"))
        connection = connect_runtime(args.db)
        try:
            result = persist_episode(connection, episode)
        finally:
            connection.close()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, KeyError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"evidence store failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
