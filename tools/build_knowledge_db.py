#!/usr/bin/env python3
"""Build RepoHarvester's local SQLite/FTS5 DevOS runtime.

Git-reviewed repository knowledge/manifests are refreshed deterministically.
Runtime feedback, evidence, and learning history are preserved across normal
rebuilds and removed only with --fresh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Iterable

try:
    from tools.db_runtime import cleanup_runtime_files, connect_runtime
    from tools.devos_tasks import load_tasks as load_effective_tasks
except ModuleNotFoundError:
    from db_runtime import cleanup_runtime_files, connect_runtime
    from devos_tasks import load_tasks as load_effective_tasks

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".build" / "repoharvester-knowledge.db"
SOURCE_REGISTRY = ROOT / "knowledge" / "sources.jsonl"
GOVERNANCE_SNAPSHOT = ROOT / "knowledge" / "governance_snapshot.json"
BRANCH_REGISTRY = ROOT / "devos" / "branches.jsonl"
TASK_REGISTRY = ROOT / "devos" / "tasks.jsonl"
OPPORTUNITY_REGISTRY = ROOT / "devos" / "opportunities.jsonl"
RECEIPT_ROOT = ROOT / "devos" / "receipts"

INCLUDED_ROOT_FILES = ("README.md", "ARCHITECTURE.md", "AGENTS.md")
INCLUDED_DOC_GLOBS = ("docs/**/*.md", "knowledge/README.md", "devos/**/*.md")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(value: object) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def markdown_sections(text: str) -> Iterable[tuple[str, str]]:
    """Yield (section, content) chunks split on H1/H2 headings."""
    section = ""
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") or line.startswith("## "):
            if buf and any(item.strip() for item in buf):
                yield section, "\n".join(buf).strip()
            section = line.lstrip("#").strip()
            buf = [line]
        else:
            buf.append(line)
    if buf and any(item.strip() for item in buf):
        yield section, "\n".join(buf).strip()


def iter_markdown_files() -> Iterable[Path]:
    seen: set[Path] = set()
    for name in INCLUDED_ROOT_FILES:
        path = ROOT / name
        if path.exists():
            seen.add(path)
            yield path
    for pattern in INCLUDED_DOC_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def validate_source(record: dict, line_number: int) -> None:
    required = {
        "id", "title", "url", "kind", "topics", "license",
        "use", "authority", "status", "notes"
    }
    missing = sorted(required - set(record))
    if missing:
        raise ValueError(
            f"{SOURCE_REGISTRY.relative_to(ROOT)} line {line_number}: "
            f"missing fields {', '.join(missing)}"
        )
    if not isinstance(record["topics"], list):
        raise ValueError(
            f"{SOURCE_REGISTRY.relative_to(ROOT)} line {line_number}: topics must be a list"
        )


def load_sources() -> list[dict]:
    records: list[dict] = []
    seen_ids: set[str] = set()
    if not SOURCE_REGISTRY.exists():
        return records
    for number, raw in enumerate(SOURCE_REGISTRY.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        record = json.loads(raw)
        validate_source(record, number)
        if record["id"] in seen_ids:
            raise ValueError(f"duplicate source id: {record['id']}")
        seen_ids.add(record["id"])
        records.append(record)
    return records


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.relative_to(ROOT)} line {number}: {exc}") from exc
    return rows


def load_governance_snapshot() -> dict:
    snapshot = json.loads(GOVERNANCE_SNAPSHOT.read_text(encoding="utf-8"))
    required = {
        "schema_version", "snapshot_id", "scope_key", "materialized_on",
        "source_repository_head", "upstream_system", "upstream_refs",
        "project_state", "claims"
    }
    missing = sorted(required - set(snapshot))
    if missing:
        raise ValueError(f"governance snapshot missing: {', '.join(missing)}")
    if snapshot["scope_key"] != "repo-harvester":
        raise ValueError("governance snapshot scope_key must be repo-harvester")
    if not isinstance(snapshot["claims"], list) or not snapshot["claims"]:
        raise ValueError("governance snapshot must contain claims")
    return snapshot


def validate_claim(claim: dict, seen: set[str]) -> None:
    required = {
        "claim_id", "branch_key", "statement", "authority_class", "lifecycle",
        "status", "source_system", "source_ref", "verified_at", "valid_through",
        "evidence", "supersedes"
    }
    missing = sorted(required - set(claim))
    if missing:
        raise ValueError(
            f"governance claim {claim.get('claim_id', '<unknown>')} missing: "
            f"{', '.join(missing)}"
        )
    if claim["claim_id"] in seen:
        raise ValueError(f"duplicate governance claim id: {claim['claim_id']}")
    seen.add(claim["claim_id"])
    if not isinstance(claim["evidence"], list):
        raise ValueError(f"{claim['claim_id']}: evidence must be a list")
    for evidence in claim["evidence"]:
        if not evidence.get("ref") or not evidence.get("independence_key"):
            raise ValueError(
                f"{claim['claim_id']}: evidence requires ref and independence_key"
            )


def reset_static_tables(connection: sqlite3.Connection) -> None:
    """Refresh repository projections without erasing runtime history."""
    for table in (
        "research_sources",
        "research_episode_branches",
        "research_episode_tasks",
        "research_episodes",
        "opportunity_sources",
        "opportunity_tasks",
        "opportunity_branches",
        "research_opportunities",
        "task_dependencies",
        "task_branches",
        "devos_tasks",
        "documents",
        "sources",
        "governance_claims_fts",
        "governance_claims",
        "branch_state",
        "governance_meta",
    ):
        connection.execute(f"DELETE FROM {table}")


def insert_documents(connection: sqlite3.Connection) -> int:
    document_count = 0
    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        title = first_heading(text, path.stem)
        kind = "root" if path.parent == ROOT else "documentation"
        section_counts: dict[str, int] = {}
        for section, content in markdown_sections(text):
            section_counts[section] = section_counts.get(section, 0) + 1
            stored_section = section
            if section_counts[section] > 1:
                stored_section = f"{section} [{section_counts[section]}]"
            connection.execute(
                """
                INSERT INTO documents(path, title, section, content, content_hash, kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (relative, title, stored_section, content, sha256_text(content), kind),
            )
            document_count += 1
    return document_count


def insert_sources(connection: sqlite3.Connection) -> int:
    sources = load_sources()
    for source in sources:
        canonical = json.dumps(source, sort_keys=True, separators=(",", ":"))
        connection.execute(
            """
            INSERT INTO sources(
                source_id, title, url, kind, topics_json, license,
                use_text, authority, status, notes, source_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["id"], source["title"], source["url"], source["kind"],
                json.dumps(source["topics"], sort_keys=True), source["license"],
                source["use"], source["authority"], source["status"],
                source["notes"], sha256_text(canonical),
            ),
        )
    return len(sources)


def insert_governance(connection: sqlite3.Connection) -> int:
    snapshot = load_governance_snapshot()
    meta = {
        "snapshot_id": snapshot["snapshot_id"],
        "scope_key": snapshot["scope_key"],
        "materialized_on": snapshot["materialized_on"],
        "source_repository_head": snapshot["source_repository_head"],
        "upstream_system": snapshot["upstream_system"],
        "project_state": json.dumps(snapshot["project_state"], sort_keys=True),
        "upstream_refs": json.dumps(snapshot["upstream_refs"], sort_keys=True),
        "snapshot_hash": sha256_text(GOVERNANCE_SNAPSHOT.read_text(encoding="utf-8")),
    }
    connection.executemany(
        "INSERT INTO governance_meta(key, value) VALUES (?, ?)",
        sorted(meta.items()),
    )

    seen: set[str] = set()
    for claim in snapshot["claims"]:
        validate_claim(claim, seen)
        evidence = claim["evidence"]
        support_count = len(evidence)
        independent_support_count = len({item["independence_key"] for item in evidence})
        canonical = json.dumps(claim, sort_keys=True, separators=(",", ":"))
        connection.execute(
            """
            INSERT INTO governance_claims(
                claim_id, branch_key, statement, authority_class, lifecycle,
                status, source_system, source_ref, evidence_json, support_count,
                independent_support_count, verified_at, valid_through,
                supersedes_json, claim_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim["claim_id"], claim["branch_key"], claim["statement"],
                claim["authority_class"], claim["lifecycle"], claim["status"],
                claim["source_system"], claim["source_ref"],
                json.dumps(evidence, sort_keys=True), support_count,
                independent_support_count, claim["verified_at"],
                claim["valid_through"], json.dumps(claim["supersedes"], sort_keys=True),
                sha256_text(canonical),
            ),
        )
        connection.execute(
            """
            INSERT INTO governance_claims_fts(
                claim_id, statement, branch_key, authority_class, lifecycle, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                claim["claim_id"], claim["statement"], claim["branch_key"],
                claim["authority_class"], claim["lifecycle"], claim["status"],
            ),
        )
    return len(snapshot["claims"])


def insert_branch_state(connection: sqlite3.Connection) -> int:
    branches = load_jsonl(BRANCH_REGISTRY)
    seen: set[str] = set()
    for row in branches:
        key = row.get("branch_key")
        if not key:
            raise ValueError("branch registry row missing branch_key")
        if key in seen:
            raise ValueError(f"duplicate branch key: {key}")
        seen.add(key)
        connection.execute(
            """
            INSERT INTO branch_state(
                branch_key, status, branch_type, owner_agent, github_paths_json,
                dependencies_json, exclusions_json, retrieval_packet, upstream_ref,
                tracking_json, row_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key, row["status"], row["branch_type"], row["owner_agent"],
                json.dumps(row["github_paths"], sort_keys=True),
                json.dumps(row["dependencies"], sort_keys=True),
                json.dumps(row["exclusions"], sort_keys=True), row["retrieval_packet"],
                row["notion_page"], json.dumps(row["tracking"], sort_keys=True),
                canonical_hash(row),
            ),
        )
    return len(branches)


def insert_tasks(connection: sqlite3.Connection) -> int:
    tasks = load_effective_tasks()
    ids = {row["task_id"] for row in tasks}
    for row in tasks:
        connection.execute(
            """
            INSERT INTO devos_tasks(
                task_id, title, priority, status, task_type, owner_role,
                assigned_agent, objective, transfer_canary, tracking_json,
                acceptance_json, evidence_refs_json, manifest_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["task_id"], row["title"], row["priority"], row["status"],
                row["task_type"], row["owner_role"], row.get("assigned_agent"),
                row["objective"], int(row["transfer_canary"]),
                json.dumps(row["tracking"], sort_keys=True),
                json.dumps(row["acceptance"], sort_keys=True),
                json.dumps(row["evidence_refs"], sort_keys=True), canonical_hash(row),
            ),
        )
    for row in tasks:
        for ordinal, branch_key in enumerate(row["branch_keys"]):
            connection.execute(
                "INSERT INTO task_branches(task_id, branch_key, ordinal) VALUES (?, ?, ?)",
                (row["task_id"], branch_key, ordinal),
            )
        for ordinal, dependency in enumerate(row["depends_on"]):
            if dependency not in ids:
                raise ValueError(f"{row['task_id']}: unknown dependency {dependency}")
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_task_id, ordinal) VALUES (?, ?, ?)",
                (row["task_id"], dependency, ordinal),
            )
    return len(tasks)


def insert_opportunities(connection: sqlite3.Connection) -> int:
    rows = load_jsonl(OPPORTUNITY_REGISTRY)
    for row in rows:
        connection.execute(
            """
            INSERT INTO research_opportunities(
                opportunity_id, title, status, need, proposal, expected_value,
                novelty_reason, project_fit, risks_json, validation_plan_json,
                cross_reference_disposition, suggested_disposition,
                authority_effect, promotion_state, manifest_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["opportunity_id"], row["title"], row["status"], row["need"],
                row["proposal"], row["expected_value"], row["novelty_reason"],
                row["project_fit"], json.dumps(row["risks"], sort_keys=True),
                json.dumps(row["validation_plan"], sort_keys=True),
                row["cross_reference_disposition"], row["suggested_disposition"],
                row["authority_effect"], row["promotion_state"], canonical_hash(row),
            ),
        )
        for ordinal, branch_key in enumerate(row["branch_keys"]):
            connection.execute(
                "INSERT INTO opportunity_branches(opportunity_id, branch_key, ordinal) VALUES (?, ?, ?)",
                (row["opportunity_id"], branch_key, ordinal),
            )
        for ordinal, task_id in enumerate(row["trigger_task_ids"]):
            connection.execute(
                "INSERT INTO opportunity_tasks(opportunity_id, task_id, ordinal) VALUES (?, ?, ?)",
                (row["opportunity_id"], task_id, ordinal),
            )
        for kind, values in (("source", row["source_refs"]), ("evidence", row["evidence_refs"])):
            for ordinal, ref in enumerate(values):
                connection.execute(
                    "INSERT INTO opportunity_sources(opportunity_id, source_ref, source_kind, ordinal) VALUES (?, ?, ?, ?)",
                    (row["opportunity_id"], ref, kind, ordinal),
                )
    return len(rows)


def iter_research_receipts() -> Iterable[tuple[Path, dict]]:
    if not RECEIPT_ROOT.exists():
        return
    for path in sorted(RECEIPT_ROOT.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.relative_to(ROOT)}: {exc}") from exc
        if isinstance(payload, dict) and payload.get("research_id"):
            yield path, payload


def insert_research_receipts(connection: sqlite3.Connection) -> int:
    count = 0
    for path, row in iter_research_receipts():
        raw = path.read_text(encoding="utf-8")
        connection.execute(
            """
            INSERT INTO research_episodes(
                research_id, trigger_signals_json, questions_json, queries_json,
                claims_json, uncertainties_json, inspirations_json,
                opportunities_json, no_op_reason, authority_effect,
                promotion_state, receipt_path, receipt_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["research_id"], json.dumps(row["trigger_signals"], sort_keys=True),
                json.dumps(row["questions"], sort_keys=True),
                json.dumps(row["queries"], sort_keys=True),
                json.dumps(row["claims"], sort_keys=True),
                json.dumps(row["uncertainties"], sort_keys=True),
                json.dumps(row["inspirations"], sort_keys=True),
                json.dumps(row["opportunities"], sort_keys=True), row.get("no_op_reason"),
                row["authority_effect"], row["promotion_state"],
                path.relative_to(ROOT).as_posix(), sha256_text(raw),
            ),
        )
        for ordinal, task_id in enumerate(row["trigger_task_ids"]):
            connection.execute(
                "INSERT INTO research_episode_tasks(research_id, task_id, ordinal) VALUES (?, ?, ?)",
                (row["research_id"], task_id, ordinal),
            )
        for ordinal, branch_key in enumerate(row["branch_keys"]):
            connection.execute(
                "INSERT INTO research_episode_branches(research_id, branch_key, ordinal) VALUES (?, ?, ?)",
                (row["research_id"], branch_key, ordinal),
            )
        for ordinal, source in enumerate(row["sources"]):
            connection.execute(
                """
                INSERT INTO research_sources(
                    research_id, source_ref, source_class, title,
                    published_or_updated, retrieved_on, ordinal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["research_id"], source["source_ref"], source["source_class"],
                    source["title"], source.get("published_or_updated"),
                    source["retrieved_on"], ordinal,
                ),
            )
        count += 1
    return count


def build(db_path: Path, *, fresh: bool = False) -> tuple[int, int]:
    """Build repository projections while preserving runtime state."""
    if fresh:
        cleanup_runtime_files(db_path)

    connection = connect_runtime(db_path)
    try:
        reset_static_tables(connection)
        document_count = insert_documents(connection)
        source_count = insert_sources(connection)
        insert_governance(connection)
        insert_branch_state(connection)
        insert_tasks(connection)
        insert_opportunities(connection)
        insert_research_receipts(connection)
        connection.commit()

        # Exercise FTS integrity and refresh planner statistics after rebuild.
        connection.execute(
            "SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ?",
            ("project",),
        ).fetchone()
        connection.execute(
            "SELECT count(*) FROM governance_claims_fts WHERE governance_claims_fts MATCH ?",
            ("project",),
        ).fetchone()
        connection.execute("PRAGMA optimize")
        return document_count, source_count
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build into a temporary check database and remove it after validation.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete the target database first, including runtime history.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.db
    fresh = args.fresh
    if args.check:
        target = ROOT / ".build" / "repoharvester-knowledge.check.db"
        cleanup_runtime_files(target)
        fresh = True
    document_count, source_count = build(target, fresh=fresh)
    if args.check:
        cleanup_runtime_files(target)
    else:
        print(f"built {target} documents={document_count} sources={source_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
