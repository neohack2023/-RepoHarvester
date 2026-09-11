"""Run the TypeScript symbol-record acceptance gate against an exact Git revision."""

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


def run_acceptance(repository_url: str, revision: str, slug: str, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="repoharvester-symbol-acceptance-") as temp_dir:
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
        symbol_records = build_typescript_symbol_records(file_records)
        if not symbol_records:
            raise RuntimeError("TypeScript symbol acceptance produced zero symbol records")
        if {record.qualification_state for record in symbol_records} != {QualificationState.RAW}:
            raise RuntimeError("symbol extraction promoted records beyond RAW")
        if {record.source_revision for record in symbol_records} != {revision}:
            raise RuntimeError("symbol records are not bound exclusively to the pinned revision")

        records = [*file_records, *symbol_records]
        database_path = output_dir / "harvest.sqlite3"
        if database_path.exists():
            database_path.unlink()
        store = SQLiteHarvestStore(database_path)
        store.upsert_records(records)
        reloaded_symbols = store.query_records(
            source_repository=repository_url,
            source_revision=revision,
            unit_kind="symbol",
            language="TypeScript",
        )
        if reloaded_symbols != symbol_records:
            raise RuntimeError("SQLite symbol round-trip differs from deterministic extraction")

        probe = symbol_records[len(symbol_records) // 2]
        exact = store.query_records(
            source_repository=repository_url,
            source_revision=revision,
            path=probe.path,
            unit_kind="symbol",
            unit_identity=probe.unit_identity,
        )
        if exact != [probe]:
            raise RuntimeError("exact symbol identity query did not reproduce the selected symbol")

        reloaded_all = store.query_records(
            source_repository=repository_url,
            source_revision=revision,
        )
        receipt = build_extraction_receipt(
            reloaded_all,
            next_gate="validate TypeScript symbol coverage before adding another language",
        )
        if not verify_extraction_receipt(receipt, reloaded_all):
            raise RuntimeError("symbol extraction receipt failed reproduction verification")
        write_extraction_receipt(output_dir / "EXTRACTION_RECEIPT.json", receipt)

        status_after = _git("status", "--porcelain", cwd=checkout)
        if status_before != status_after or status_after:
            raise RuntimeError("symbol harvest mutated the external source checkout")

        symbol_kinds = Counter(
            tag.removeprefix("symbol:")
            for record in symbol_records
            for tag in record.tags
            if tag.startswith("symbol:")
        )
        summary = {
            "source_repository": repository_url,
            "source_revision": revision,
            "file_record_count": len(file_records),
            "typescript_file_count": sum(record.language == "TypeScript" for record in file_records),
            "symbol_record_count": len(symbol_records),
            "database_record_count": len(reloaded_all),
            "qualification_states": sorted({record.qualification_state.value for record in symbol_records}),
            "symbol_kinds": dict(sorted(symbol_kinds.items())),
            "exact_symbol_probe": probe.unit_identity,
            "receipt_version": receipt.receipt_version,
            "manifest_sha256": receipt.manifest_sha256,
            "source_worktree_clean": True,
            "receipt_verified": True,
            "typescript_symbol_gate": "PASS",
        }
        (output_dir / "SYMBOL_ACCEPTANCE_SUMMARY.json").write_text(
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
