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
    build_typescript_symbol_records,
    verify_extraction_receipt,
    write_extraction_receipt,
)
from repoharvester.storage import SQLiteHarvestStore

DEFAULT_IGNORES = {".git", "*.pyc", "__pycache__", "node_modules"}


def _git(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
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
    return (
        record.source_repository,
        record.source_revision,
        record.path,
        record.unit_kind,
        record.unit_identity,
    )


def run_acceptance(repository_url: str, revision: str, slug: str, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="repoharvester-acceptance-") as temp_dir:
        checkout = Path(temp_dir) / "source"
        checkout.mkdir()
        _checkout_exact_revision(repository_url, revision, checkout)
        status_before = _git("status", "--porcelain", cwd=checkout)

        query = IngestionQuery(
            local_path=checkout,
            url=repository_url,
            slug=slug,
            id=uuid4(),
            commit=revision,
            ignore_patterns=DEFAULT_IGNORES,
        )
        file_records = build_file_harvest_records(query)
        if not file_records:
            raise RuntimeError("acceptance harvest produced zero file records")

        symbol_records = [
            symbol
            for file_record in file_records
            for symbol in build_typescript_symbol_records(file_record)
        ]
        if not symbol_records:
            raise RuntimeError("TypeScript symbol acceptance produced zero code-unit records")
        records = [*file_records, *symbol_records]

        if {record.source_revision for record in records} != {revision}:
            raise RuntimeError("harvest records do not bind exclusively to the pinned revision")
        if {record.qualification_state for record in records} != {QualificationState.RAW}:
            raise RuntimeError("acceptance harvest promoted records beyond RAW")
        if any(record.start_byte is None or record.end_byte is None for record in symbol_records):
            raise RuntimeError("symbol records are missing exact source spans")
        if any(not record.unit_identity for record in symbol_records):
            raise RuntimeError("symbol records are missing stable unit identities")

        database_path = output_dir / "harvest.sqlite3"
        if database_path.exists():
            database_path.unlink()
        store = SQLiteHarvestStore(database_path)
        stored_count = store.upsert_records(records)
        reloaded = store.query_records(source_repository=repository_url, source_revision=revision)
        if stored_count != len(records) or len(reloaded) != len(records):
            raise RuntimeError("SQLite round-trip record count mismatch")
        if sorted(map(_record_identity, reloaded)) != sorted(map(_record_identity, records)):
            raise RuntimeError("SQLite exact-query identities differ from harvested identities")

        symbol_names = {record.symbol_name for record in symbol_records}
        known_symbol = next((name for name in sorted(symbol_names) if name), None)
        if known_symbol is None:
            raise RuntimeError("symbol acceptance produced no named symbols")
        exact_symbol_query = store.query_records(
            source_repository=repository_url,
            source_revision=revision,
            symbol_name=known_symbol,
        )
        if not exact_symbol_query or any(record.symbol_name != known_symbol for record in exact_symbol_query):
            raise RuntimeError("SQLite exact symbol query failed")

        receipt = build_extraction_receipt(
            reloaded,
            warnings=(),
            next_gate="TypeScript code-unit extraction proven; evaluate next language or qualification slice",
        )
        if not verify_extraction_receipt(receipt, reloaded):
            raise RuntimeError("extraction receipt failed reproduction verification")
        receipt_path = output_dir / "EXTRACTION_RECEIPT.json"
        write_extraction_receipt(receipt_path, receipt)

        status_after = _git("status", "--porcelain", cwd=checkout)
        if status_before != status_after or status_after:
            raise RuntimeError("harvest mutated the external source checkout")

        languages = Counter(record.language or "Unknown" for record in records)
        role_tags = Counter(
            tag
            for record in records
            for tag in record.tags
            if tag.startswith("role:")
        )
        symbol_kinds = Counter(record.unit_kind for record in symbol_records)
        summary = {
            "source_repository": repository_url,
            "source_revision": revision,
            "file_record_count": len(file_records),
            "symbol_record_count": len(symbol_records),
            "record_count": len(records),
            "database_record_count": len(reloaded),
            "qualification_states": sorted({record.qualification_state.value for record in records}),
            "tag_rulesets": sorted({record.tag_ruleset for record in records if record.tag_ruleset}),
            "languages": dict(sorted(languages.items())),
            "roles": dict(sorted(role_tags.items())),
            "symbol_kinds": dict(sorted(symbol_kinds.items())),
            "exact_symbol_query_example": known_symbol,
            "manifest_sha256": receipt.manifest_sha256,
            "source_worktree_clean": True,
            "receipt_verified": True,
            "typescript_symbol_gate": "PASS",
        }
        (output_dir / "ACCEPTANCE_SUMMARY.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run_acceptance(args.repository_url, args.revision, args.slug, args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
