"""Generic repository-to-corpus harvesting without qualification promotion."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from gitingest.schemas import IngestionQuery

from repoharvester.dependencies import build_declared_dependency_records
from repoharvester.licenses import build_repository_license_records
from repoharvester.models import HarvestRecord, HarvestRelationship, QualificationState
from repoharvester.python_relationships import build_python_relationships
from repoharvester.python_symbols import PythonParseError, build_python_symbol_records
from repoharvester.receipts import ExtractionReceipt, build_extraction_receipt, verify_extraction_receipt
from repoharvester.records import build_file_harvest_records
from repoharvester.relationships import build_typescript_relationships
from repoharvester.storage import SQLiteHarvestStore
from repoharvester.symbols import TypeScriptParseError, build_typescript_symbol_records


@dataclass(frozen=True)
class CorpusHarvestResult:
    """One exact repository/revision harvest persisted into a shared corpus."""

    records: tuple[HarvestRecord, ...]
    relationships: tuple[HarvestRelationship, ...]
    receipt: ExtractionReceipt
    summary: dict[str, object]


@dataclass(frozen=True)
class _RecordBuildResult:
    records: tuple[HarvestRecord, ...]
    warnings: tuple[str, ...]
    skipped_typescript_paths: tuple[str, ...]
    skipped_python_paths: tuple[str, ...]


def _record_identity(record: HarvestRecord) -> tuple[str, str, str, str, str]:
    return (
        record.source_repository,
        record.source_revision,
        record.path,
        record.unit_kind,
        record.unit_identity,
    )


def _build_records(query: IngestionQuery) -> _RecordBuildResult:
    file_records = build_file_harvest_records(query)
    symbol_records: list[HarvestRecord] = []
    warnings: list[str] = []
    skipped_typescript_paths: list[str] = []
    skipped_python_paths: list[str] = []

    for file_record in file_records:
        try:
            symbol_records.extend(build_typescript_symbol_records(file_record))
        except TypeScriptParseError:
            skipped_typescript_paths.append(file_record.path)
            warnings.append(
                f"semantic-extraction-skipped:{file_record.path}:typescript-parse-error"
            )

        try:
            symbol_records.extend(build_python_symbol_records(file_record))
        except PythonParseError:
            skipped_python_paths.append(file_record.path)
            warnings.append(
                f"semantic-extraction-skipped:{file_record.path}:python-parse-error"
            )

    license_records = build_repository_license_records(file_records)
    dependency_records = build_declared_dependency_records(file_records)
    records = tuple((*file_records, *symbol_records, *license_records, *dependency_records))
    return _RecordBuildResult(
        records=records,
        warnings=tuple(sorted(warnings)),
        skipped_typescript_paths=tuple(sorted(skipped_typescript_paths)),
        skipped_python_paths=tuple(sorted(skipped_python_paths)),
    )


def harvest_into_corpus(
    query: IngestionQuery,
    database_path: str | Path,
    *,
    warnings: Iterable[str] = (),
    next_gate: str = "TAGGING_CALIBRATION_01",
) -> CorpusHarvestResult:
    """Harvest one exact checkout and upsert it into a shared SQLite corpus.

    This operation is deliberately qualification-neutral. Every newly harvested
    record must remain RAW. Existing records for other repositories/revisions in
    the database are preserved. Unsupported TypeScript or Python syntax degrades
    semantic coverage for the affected files only; file/provenance evidence is
    retained and the omission is bound into the extraction receipt as an explicit
    warning.
    """

    build_result = _build_records(query)
    records = build_result.records
    relationships = tuple(
        sorted(
            (
                *build_typescript_relationships(
                    records,
                    skip_source_paths=build_result.skipped_typescript_paths,
                ),
                *build_python_relationships(
                    records,
                    skip_source_paths=build_result.skipped_python_paths,
                ),
            ),
            key=lambda item: (
                item.source_repository,
                item.source_revision,
                item.source_path,
                item.source_unit_kind,
                item.source_unit_identity,
                item.relationship_kind,
                item.target_path,
                item.target_unit_kind,
                item.target_unit_identity,
                item.literal_target,
                item.start_byte if item.start_byte is not None else -1,
                item.end_byte if item.end_byte is not None else -1,
                item.start_row if item.start_row is not None else -1,
                item.start_column if item.start_column is not None else -1,
            ),
        )
    )

    if not records:
        raise RuntimeError("corpus harvest produced no records")
    if {record.source_repository for record in records} != {query.url}:
        raise RuntimeError("harvest records do not bind exclusively to the requested repository")
    if {record.source_revision for record in records} != {query.commit}:
        raise RuntimeError("harvest records do not bind exclusively to the requested revision")
    if {record.qualification_state for record in records} != {QualificationState.RAW}:
        raise RuntimeError("generic corpus harvest must not promote records beyond RAW")

    combined_warnings = tuple((*warnings, *build_result.warnings))
    receipt = build_extraction_receipt(
        records,
        relationships=relationships,
        warnings=combined_warnings,
        next_gate=next_gate,
    )
    if not verify_extraction_receipt(receipt, records, relationships=relationships):
        raise RuntimeError("corpus extraction receipt failed reproduction verification")

    store = SQLiteHarvestStore(database_path)
    stored_count = store.upsert_records(records)
    stored_relationship_count = store.upsert_relationships(relationships)
    reloaded = store.query_records(source_repository=query.url, source_revision=query.commit)
    reloaded_relationships = store.query_relationships(
        source_repository=query.url,
        source_revision=query.commit,
    )

    if stored_count != len(records) or len(reloaded) != len(records):
        raise RuntimeError("SQLite corpus record round-trip mismatch")
    if stored_relationship_count != len(relationships) or reloaded_relationships != list(relationships):
        raise RuntimeError("SQLite corpus relationship round-trip mismatch")
    if sorted(map(_record_identity, reloaded)) != sorted(map(_record_identity, records)):
        raise RuntimeError("SQLite corpus identities differ from harvested identities")

    unit_kinds = Counter(record.unit_kind for record in records)
    languages = Counter(record.language or "unknown" for record in records)
    relationship_kinds = Counter(item.relationship_kind for item in relationships)
    resolution_states = Counter(item.resolution_state.value for item in relationships)
    skipped_semantic_paths = sorted(
        (*build_result.skipped_typescript_paths, *build_result.skipped_python_paths)
    )

    summary: dict[str, object] = {
        "source_repository": query.url,
        "source_revision": query.commit,
        "record_count": len(records),
        "relationship_count": len(relationships),
        "unit_kinds": dict(sorted(unit_kinds.items())),
        "languages": dict(sorted(languages.items())),
        "relationship_kinds": dict(sorted(relationship_kinds.items())),
        "resolution_states": dict(sorted(resolution_states.items())),
        "manifest_sha256": receipt.manifest_sha256,
        "relationship_manifest_sha256": receipt.relationship_manifest_sha256,
        "receipt_verified": True,
        "warnings": list(receipt.warnings),
        "semantic_skip_count": len(skipped_semantic_paths),
        "semantic_skipped_paths": skipped_semantic_paths,
        "qualification_state": "RAW",
        "qualification_performed": False,
        "corpus_database": str(Path(database_path)),
    }

    return CorpusHarvestResult(
        records=records,
        relationships=relationships,
        receipt=receipt,
        summary=summary,
    )
