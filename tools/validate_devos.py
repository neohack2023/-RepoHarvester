#!/usr/bin/env python3
"""Validate RepoHarvester DevOS routing and repository-autonomy metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEVOS = ROOT / "devos"
PROJECT_FILE = DEVOS / "project.json"
BRANCH_FILE = DEVOS / "branches.jsonl"
TOOL_FILE = DEVOS / "tools.jsonl"
LOCK_FILE = DEVOS / "governance-lock.json"

ALLOWED_STATUS = {"active", "incubating", "candidate", "paused", "archived", "superseded"}
ALLOWED_TYPE = {"core", "feature", "simulation", "runtime", "tooling", "research"}
ALLOWED_TOOL_MATURITY = {"candidate", "verified", "deprecated"}
ALLOWED_CAPABILITY_QUALIFICATION = {"candidate", "verified", "unsupported"}
REQUIRED_BRANCH_FIELDS = {
    "branch_key",
    "status",
    "branch_type",
    "owner_agent",
    "github_paths",
    "notion_page",
    "dependencies",
    "exclusions",
    "retrieval_packet",
    "tracking",
}
REQUIRED_TOOL_FIELDS = {
    "tool_key",
    "repository",
    "verified_revision",
    "usage_contract",
    "maturity",
    "capabilities",
    "known_limits",
    "entrypoints",
    "evidence",
    "last_verified",
}
REQUIRED_CAPABILITY_FIELDS = {"name", "scope", "languages", "qualification"}


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_project() -> dict:
    project = json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    required = {
        "schema_version", "scope_key", "project_name", "repository",
        "authority", "local_runtime", "notion", "governance", "default_agent",
        "branch_registry", "bootstrap_status"
    }
    missing = sorted(required - set(project))
    if missing:
        raise ValueError(f"project.json missing: {', '.join(missing)}")
    if project["scope_key"] != "repo-harvester":
        raise ValueError("project.json scope_key must be repo-harvester")
    if project["repository"] != "neohack2023/repo-harvester":
        raise ValueError("project.json repository mismatch")
    if project["branch_registry"] != "devos/branches.jsonl":
        raise ValueError("project.json branch_registry mismatch")

    notion = project["notion"]
    for field in (
        "memory_root", "project_handoff", "retrieval_index",
        "knowledge_branch_registry", "scope_registry_record",
        "stone_skill", "mason_ledger", "runtime_use"
    ):
        if not notion.get(field):
            raise ValueError(f"project.json notion.{field} is required")
    if notion["runtime_use"] != "explicit_sync_only":
        raise ValueError("Notion runtime_use must be explicit_sync_only")

    local = project["local_runtime"]
    for field in (
        "knowledge_db", "governance_snapshot", "governance_lock",
        "query_tool", "feedback_table", "tool_registry"
    ):
        if not local.get(field):
            raise ValueError(f"project.json local_runtime.{field} is required")

    governance = project["governance"]
    if governance.get("normal_repo_work_external_fetch_required") is not False:
        raise ValueError(
            "normal repository work must not require external governance fetch"
        )
    if governance.get("prevalence_can_upgrade_authority") is not False:
        raise ValueError("prevalence must never upgrade authority")
    return project


def load_branches() -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(BRANCH_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        missing = sorted(REQUIRED_BRANCH_FIELDS - set(row))
        extra = sorted(set(row) - REQUIRED_BRANCH_FIELDS)
        if missing:
            raise ValueError(f"branches.jsonl line {line_no} missing: {', '.join(missing)}")
        if extra:
            raise ValueError(f"branches.jsonl line {line_no} extra fields: {', '.join(extra)}")
        rows.append(row)
    if not rows:
        raise ValueError("branches.jsonl contains no branches")
    return rows


def load_tools() -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(TOOL_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        missing = sorted(REQUIRED_TOOL_FIELDS - set(row))
        extra = sorted(set(row) - REQUIRED_TOOL_FIELDS)
        if missing:
            raise ValueError(f"tools.jsonl line {line_no} missing: {', '.join(missing)}")
        if extra:
            raise ValueError(f"tools.jsonl line {line_no} extra fields: {', '.join(extra)}")
        rows.append(row)
    if not rows:
        raise ValueError("tools.jsonl contains no tools")
    return rows


def load_lock() -> dict:
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    required = {
        "schema_version", "bundle_id", "bundle_version", "state",
        "materialized_on", "valid_through",
        "normal_repo_work_external_fetch_required",
        "upstream_authority_cutover", "local_runtime",
        "projection_sha256", "sync_state", "sync_contract",
        "sync_receipt_root", "last_sync_id", "last_sync_receipt",
        "last_sync_receipt_sha256", "last_upstream_sync",
        "sync_freshness_days", "external_fetch_triggers",
        "staleness_behavior", "prevalence_policy",
        "live_repository_facts_source", "durable_project_memory_source",
        "repository_runtime_context_source"
    }
    missing = sorted(required - set(lock))
    if missing:
        raise ValueError(f"governance-lock.json missing: {', '.join(missing)}")
    if lock["normal_repo_work_external_fetch_required"] is not False:
        raise ValueError("governance lock must keep normal repo work local")
    if lock["upstream_authority_cutover"] is not False:
        raise ValueError("repository projection cannot imply authority cutover")
    if lock["staleness_behavior"]["review_flag_on_age_alone"] is not False:
        raise ValueError("projection age alone must not create review state")
    if lock["staleness_behavior"]["projection_age_is_authority_downgrade"] is not False:
        raise ValueError("projection age alone must not downgrade authority")
    if lock["prevalence_policy"]["prevalence_can_upgrade_authority"] is not False:
        raise ValueError("prevalence must not upgrade authority")
    return lock


def validate_local_runtime(project: dict, lock: dict, errors: list[str]) -> None:
    local = project["local_runtime"]
    for field in ("governance_snapshot", "governance_lock", "query_tool", "tool_registry"):
        relative = local[field]
        if not (ROOT / relative).exists():
            errors.append(f"local runtime path missing: {relative}")

    if local["governance_lock"] != "devos/governance-lock.json":
        errors.append("project local governance_lock path mismatch")
    if local["tool_registry"] != "devos/tools.jsonl":
        errors.append("project local tool_registry path mismatch")
    if local["governance_snapshot"] != lock["local_runtime"]["governance_snapshot"]:
        errors.append("project and lock governance snapshot paths disagree")
    if local["knowledge_db"] != lock["local_runtime"]["knowledge_db"]:
        errors.append("project and lock knowledge DB paths disagree")
    if project["branch_registry"] != lock["local_runtime"]["branch_registry"]:
        errors.append("project and lock branch registry paths disagree")

    snapshot_path = ROOT / local["governance_snapshot"]
    receipt_path = ROOT / lock["last_sync_receipt"]
    if not receipt_path.exists():
        errors.append(f"sync receipt missing: {lock['last_sync_receipt']}")
    elif lock["last_sync_receipt_sha256"] != "BOOTSTRAP_UNVERIFIED" and sha256_file(receipt_path) != lock["last_sync_receipt_sha256"]:
        errors.append("sync receipt SHA-256 mismatch")

    if snapshot_path.exists():
        if lock["projection_sha256"] != "BOOTSTRAP_UNVERIFIED" and sha256_file(snapshot_path) != lock["projection_sha256"]:
            errors.append("governance projection SHA-256 mismatch")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if snapshot.get("scope_key") != "repo-harvester":
            errors.append("governance snapshot scope mismatch")
        if not snapshot.get("claims"):
            errors.append("governance snapshot contains no claims")


def validate_tools(tools: list[dict], errors: list[str]) -> None:
    keys = [row["tool_key"] for row in tools]
    if len(keys) != len(set(keys)):
        errors.append("tool keys must be unique")

    for row in tools:
        key = row["tool_key"]
        if not key or key != key.lower() or " " in key:
            errors.append(f"{key!r}: tool_key must be lowercase and space-free")
        if not re.fullmatch(r"[^/]+/[^/]+", row["repository"]):
            errors.append(f"{key}: repository must be owner/name")
        if not re.fullmatch(r"[0-9a-f]{40}", row["verified_revision"]):
            errors.append(f"{key}: verified_revision must be a full 40-char commit SHA")
        if not row["usage_contract"].strip():
            errors.append(f"{key}: usage_contract required")
        if row["maturity"] not in ALLOWED_TOOL_MATURITY:
            errors.append(f"{key}: invalid maturity {row['maturity']}")
        if not row["capabilities"]:
            errors.append(f"{key}: at least one capability required")
        if not row["known_limits"]:
            errors.append(f"{key}: known_limits required")
        if not row["entrypoints"]:
            errors.append(f"{key}: entrypoints required")
        if not row["evidence"]:
            errors.append(f"{key}: evidence required")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["last_verified"]):
            errors.append(f"{key}: last_verified must be YYYY-MM-DD")

        capability_names: list[str] = []
        for index, capability in enumerate(row["capabilities"], 1):
            missing = sorted(REQUIRED_CAPABILITY_FIELDS - set(capability))
            extra = sorted(set(capability) - REQUIRED_CAPABILITY_FIELDS)
            if missing:
                errors.append(f"{key}: capability {index} missing: {', '.join(missing)}")
                continue
            if extra:
                errors.append(f"{key}: capability {index} extra fields: {', '.join(extra)}")
            name = capability["name"]
            capability_names.append(name)
            if not name.strip() or not capability["scope"].strip():
                errors.append(f"{key}: capability {index} name/scope required")
            if not capability["languages"]:
                errors.append(f"{key}: capability {name} languages required")
            if capability["qualification"] not in ALLOWED_CAPABILITY_QUALIFICATION:
                errors.append(f"{key}: capability {name} invalid qualification {capability['qualification']}")
        if len(capability_names) != len(set(capability_names)):
            errors.append(f"{key}: capability names must be unique")


def validate() -> tuple[int, list[str]]:
    project = load_project()
    lock = load_lock()
    branches = load_branches()
    tools = load_tools()
    errors: list[str] = []
    keys = [row["branch_key"] for row in branches]
    known = set(keys)
    if len(keys) != len(known):
        errors.append("branch keys must be unique")
    if "project-core" not in known:
        errors.append("project-core branch is required")
    if "tooling-agent-harness" not in known:
        errors.append("tooling-agent-harness branch is required")

    for row in branches:
        key = row["branch_key"]
        if row["status"] not in ALLOWED_STATUS:
            errors.append(f"{key}: invalid status {row['status']}")
        if row["branch_type"] not in ALLOWED_TYPE:
            errors.append(f"{key}: invalid branch_type {row['branch_type']}")
        if not row["owner_agent"].strip():
            errors.append(f"{key}: owner_agent required")
        if not row["github_paths"]:
            errors.append(f"{key}: at least one github path required")
        if not (row["notion_page"] == "UNRESOLVED" or row["notion_page"].startswith("https://app.notion.com/p/")):
            errors.append(f"{key}: invalid Notion provenance pointer")
        if not row["retrieval_packet"].strip():
            errors.append(f"{key}: retrieval_packet required")
        for dep in row["dependencies"]:
            if dep not in known:
                errors.append(f"{key}: unknown dependency {dep}")
            if dep == key:
                errors.append(f"{key}: branch cannot depend on itself")
        for relative in row["github_paths"]:
            path = ROOT / relative
            if not path.exists():
                errors.append(f"{key}: github path does not exist: {relative}")

        if row["branch_type"] == "feature":
            feature_roots = [ROOT / p for p in row["github_paths"] if p.startswith("features/")]
            if not feature_roots:
                errors.append(f"{key}: feature branch must point at docs/features/<feature>")
            for feature_root in feature_roots:
                if feature_root.is_dir():
                    for required in ("README.md", "AGENTS.md"):
                        if not (feature_root / required).exists():
                            errors.append(f"{key}: missing local {required}")

    validate_tools(tools, errors)
    validate_local_runtime(project, lock, errors)
    return len(branches), errors


def main() -> int:
    try:
        count, errors = validate()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"DevOS validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"DevOS validation error: {error}", file=sys.stderr)
        return 1
    print(f"DevOS validation passed: {count} knowledge branches; repository-local governance runtime active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
