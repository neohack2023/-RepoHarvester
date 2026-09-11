"""Run RepoHarvester's external acceptance gate against an exact Git revision."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from uuid import uuid4

from gitingest.schemas import IngestionQuery
from repoharvester import (
    QualificationState,
    build_extraction_receipt,
    build_file_harvest_records,
    build_repository_license_records,
    build_typescript_relationships,
    build_typescript_symbol_records,
    verify_extraction_receipt,
    write_extraction_receipt,
)
from repoharvester.storage import SQLiteHarvestStore

DEFAULT_IGNORES = {".git", "*.pyc", "__pycache__", "node_modules"}


def _git(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _checkout_exact_revision(repository_url: str, revision: str, destination: Path) -> None:
    _git("init", str(destination))
    _git("remote", "add", "origin", repository_url, cwd=destination)
    _git("fetch", "--depth", "1", "origin", revision, cwd=destination)
    _git("checkout", "--detach", "FETCH_HEAD", cwd=destination)
    actual = _git("rev-parse", "HEAD", cwd=destination)
    if actual != revision:
        raise RuntimeError(f"checked out {actual}, expected {revision}")


def _record_identity(record) -> tuple[str, str, str, str, str]:
    return (record.source_repository, record.source_revision, record.path, record.unit_kind, record.unit_identity)


def run_acceptance(repository_url: str, revision: str, slug: str, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="repoharvester-acceptance-") as temp_dir:
        checkout = Path(temp_dir) / "source"
        checkout.mkdir()
        _checkout_exact_revision(repository_url, revision, checkout)
        status_before = _git("status", "--porcelain", cwd=checkout)

        query = IngestionQuery(local_path=checkout, url=repository_url, slug=slug, id=uuid4(), commit=revision, ignore_patterns=DEFAULT_IGNORES)
        file_records = build_file_harvest_records(query)
        symbol_records = [symbol for file_record in file_records for symbol in build_typescript_symbol_records(file_record)]
        license_records = build_repository_license_records(file_records)
        records = [*file_records, *symbol_records, *license_records]
        relationships = build_typescript_relationships(records)

        if not file_records or not symbol_records or not relationships or not license_records:
            raise RuntimeError("acceptance harvest produced incomplete record/relationship/license evidence")
        if {record.source_revision for record in records} != {revision}:
            raise RuntimeError("harvest records do not bind exclusively to the pinned revision")
        if {record.qualification_state for record in records} != {QualificationState.RAW}:
            raise RuntimeError("acceptance harvest promoted records beyond RAW")

        database_path = output_dir / "harvest.sqlite3"
        if database_path.exists():
            database_path.unlink()
        store = SQLiteHarvestStore(database_path)
        stored_count = store.upsert_records(records)
        stored_relationship_count = store.upsert_relationships(relationships)
        reloaded = store.query_records(source_repository=repository_url, source_revision=revision)
        reloaded_relationships = store.query_relationships(source_repository=repository_url, source_revision=revision)
        if stored_count != len(records) or len(reloaded) != len(records):
            raise RuntimeError("SQLite record round-trip mismatch")
        if stored_relationship_count != len(relationships) or reloaded_relationships != relationships:
            raise RuntimeError("SQLite relationship round-trip mismatch")
        if sorted(map(_record_identity, reloaded)) != sorted(map(_record_identity, records)):
            raise RuntimeError("SQLite exact-query identities differ from harvested identities")

        imports = store.query_relationships(source_repository=repository_url, source_revision=revision, relationship_kind="imports")
        contains = store.query_relationships(source_repository=repository_url, source_revision=revision, relationship_kind="contains")
        if not imports or not contains:
            raise RuntimeError("relationship acceptance requires both imports and containment evidence")

        stored_license_evidence = store.query_records(
            source_repository=repository_url,
            source_revision=revision,
            unit_kind="evidence:repository-license",
            tags=("evidence:repository-license", "license:spdx:MIT"),
        )
        if len(stored_license_evidence) != 1 or stored_license_evidence[0].path != "LICENSE":
            raise RuntimeError("license acceptance requires one exact root MIT license evidence record")
        if stored_license_evidence[0].representation != license_records[0].representation:
            raise RuntimeError("stored license evidence changed the exact license representation")

        receipt = build_extraction_receipt(
            reloaded,
            relationships=reloaded_relationships,
            warnings=(),
            next_gate="Repository license evidence proven; begin dependency evidence slice",
        )
        if not verify_extraction_receipt(receipt, reloaded, relationships=reloaded_relationships):
            raise RuntimeError("extraction receipt failed license-aware reproduction verification")
        write_extraction_receipt(output_dir / "EXTRACTION_RECEIPT.json", receipt)

        status_after = _git("status", "--porcelain", cwd=checkout)
        if status_before != status_after or status_after:
            raise RuntimeError("harvest mutated the external source checkout")

        relationship_kinds = Counter(item.relationship_kind for item in relationships)
        resolution_states = Counter(item.resolution_state.value for item in relationships)
        license_spdx_tags = sorted(
            tag
            for record in license_records
            for tag in record.tags
            if tag.startswith("license:spdx:")
        )
        summary = {
            "source_repository": repository_url,
            "source_revision": revision,
            "file_record_count": len(file_records),
            "symbol_record_count": len(symbol_records),
            "license_evidence_record_count": len(license_records),
            "license_spdx_tags": license_spdx_tags,
            "record_count": len(records),
            "database_record_count": len(reloaded),
            "relationship_count": len(relationships),
            "database_relationship_count": len(reloaded_relationships),
            "relationship_kinds": dict(sorted(relationship_kinds.items())),
            "resolution_states": dict(sorted(resolution_states.items())),
            "qualification_states": sorted({record.qualification_state.value for record in records}),
            "manifest_sha256": receipt.manifest_sha256,
            "relationship_manifest_sha256": receipt.relationship_manifest_sha256,
            "source_worktree_clean": True,
            "receipt_verified": True,
            "typescript_relationship_gate": "PASS",
            "repository_license_gate": "PASS",
        }
        (output_dir / "ACCEPTANCE_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_acceptance(args.repository_url, args.revision, args.slug, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
