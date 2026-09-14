#!/usr/bin/env python3
"""Validate RepoHarvester's live adoption bridge to portable DevOS v0.12."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEVOS = ROOT / "devos"
BASELINE = DEVOS / "portable-baseline.json"
POLICY = DEVOS / "consumer-policy.json"
EXPECTED_UPSTREAM = "9a5364c208285261c2ca692c285fbfd651299548"
EXPECTED_VERSION = "0.12.0"
EXPECTED_SCHEMA = 8


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def run_existing_validation() -> None:
    subprocess.run([sys.executable, str(ROOT / "tools" / "validate_devos.py")], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_knowledge_db.py"), "--check"],
        cwd=ROOT,
        check=True,
    )


def load_portable_db_runtime():
    path = DEVOS / "runtime" / "db_runtime.py"
    spec = importlib.util.spec_from_file_location("repoharvester_portable_db_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load portable db_runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate() -> dict:
    baseline = load_json(BASELINE)
    policy = load_json(POLICY)

    if baseline.get("adoption_id") != "REPOHARVESTER_LIVE_ADOPTION_01":
        raise ValueError("unexpected adoption id")
    if baseline.get("upstream_repository") != "neohack2023/Dev-os":
        raise ValueError("portable upstream repository mismatch")
    if baseline.get("upstream_revision") != EXPECTED_UPSTREAM:
        raise ValueError("portable upstream revision drift")
    if baseline.get("upstream_version") != EXPECTED_VERSION:
        raise ValueError("portable version drift")
    if baseline.get("portable_schema_version") != EXPECTED_SCHEMA:
        raise ValueError("portable schema version drift")
    if baseline.get("consumer_root") != "devos":
        raise ValueError("RepoHarvester consumer root must remain lowercase devos")

    blobs = baseline.get("upstream_git_blobs")
    if not isinstance(blobs, dict) or not blobs:
        raise ValueError("upstream_git_blobs must be a non-empty object")
    verified_blobs: list[str] = []
    for relative, expected in sorted(blobs.items()):
        path = DEVOS / relative
        if not path.is_file():
            raise ValueError(f"missing portable component: devos/{relative}")
        actual = git_blob_sha(path)
        if actual != expected:
            raise ValueError(f"portable component drift: devos/{relative}: {actual} != {expected}")
        verified_blobs.append(relative)

    exception = policy.get("branch_protection_exception") or {}
    controls = policy.get("required_compensating_controls") or {}
    adapter = policy.get("portable_github_authority_adapter") or {}
    if policy.get("repository") != "neohack2023/-RepoHarvester" or policy.get("target_branch") != "main":
        raise ValueError("consumer policy scope mismatch")
    if policy.get("branch_protection_required") is not False or exception.get("approved") is not True:
        raise ValueError("unprotected-branch exception is not explicitly approved")
    if exception.get("does_not_generalize") is not True:
        raise ValueError("branch-protection exception must be host-scoped")
    for key in (
        "exact_head_ci_required",
        "devos_consumer_validation_required",
        "existing_repo_devos_validation_required",
        "checkpoint_after_green_validation",
        "force_push_forbidden",
        "remote_authority_receipt_claim_forbidden_without_protected_policy",
    ):
        if controls.get(key) is not True:
            raise ValueError(f"missing compensating control: {key}")
    if adapter.get("enabled_for_remote_promotion") is not False:
        raise ValueError("portable remote-authority adapter must stay disabled while main is unprotected")

    run_existing_validation()

    runtime = load_portable_db_runtime()
    if runtime.CURRENT_SCHEMA_VERSION != EXPECTED_SCHEMA:
        raise ValueError("portable db runtime schema mismatch")
    with tempfile.TemporaryDirectory() as temp_dir:
        db = Path(temp_dir) / "portable-v012.db"
        connection = runtime.connect_runtime(db)
        try:
            health = runtime.runtime_health(connection)
            required_tables = {
                "evidence_roots",
                "reflection_candidates",
                "learning_capabilities",
                "promotion_envelopes",
                "mason_execution_receipts",
                "github_authority_receipts",
                "github_policy_receipts",
            }
            actual_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing = sorted(required_tables - actual_tables)
            if missing:
                raise ValueError("portable schema missing tables: " + ", ".join(missing))
            if health["schema_version"] != EXPECTED_SCHEMA or health["integrity_check"] != "ok":
                raise ValueError(f"portable runtime health failed: {health}")
        finally:
            connection.close()

    return {
        "ok": True,
        "adoption_id": baseline["adoption_id"],
        "upstream_revision": EXPECTED_UPSTREAM,
        "upstream_version": EXPECTED_VERSION,
        "portable_schema_version": EXPECTED_SCHEMA,
        "verified_portable_components": verified_blobs,
        "legacy_runtime": "PRESERVED_AND_VALIDATED",
        "branch_policy": "OWNER_VALIDATED_UNPROTECTED",
        "remote_authority_adapter": "DISABLED_UNTIL_PROTECTED_POLICY",
        "authority_effect": "NONE",
    }


def main() -> int:
    try:
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
