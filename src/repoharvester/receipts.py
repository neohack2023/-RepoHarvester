"""Compact deterministic receipts for provenance-backed harvest operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from repoharvester.models import HarvestRecord, HarvestRelationship
from repoharvester.storage import SCHEMA_VERSION

RECEIPT_VERSION = "repoharvester-extraction-v3"
RECEIPT_OPERATION = "harvest-store"
DEFAULT_NEXT_GATE = "external-repository acceptance run"


@dataclass(frozen=True)
class ExtractionReceipt:
    """Compact evidence binding one harvested revision to stored evidence identities."""

    receipt_version: str
    operation: str
    source_repository: str
    source_revision: str
    record_count: int
    manifest_sha256: str
    relationship_count: int
    relationship_manifest_sha256: str
    relationship_kinds: tuple[str, ...]
    resolution_states: tuple[str, ...]
    tag_rulesets: tuple[str, ...]
    qualification_states: tuple[str, ...]
    database_schema_version: int
    warnings: tuple[str, ...]
    next_gate: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_extraction_receipt(
    records: Iterable[HarvestRecord],
    *,
    relationships: Iterable[HarvestRelationship] = (),
    warnings: Iterable[str] = (),
    next_gate: str = DEFAULT_NEXT_GATE,
    database_schema_version: int = SCHEMA_VERSION,
) -> ExtractionReceipt:
    materialized = list(records)
    materialized_relationships = list(relationships)
    if not materialized:
        raise ValueError("extraction receipts require at least one harvest record")

    repositories = {record.source_repository for record in materialized}
    revisions = {record.source_revision for record in materialized}
    relationship_repositories = {item.source_repository for item in materialized_relationships}
    relationship_revisions = {item.source_revision for item in materialized_relationships}
    if len(repositories) != 1 or len(revisions) != 1:
        raise ValueError("extraction receipts require exactly one source repository and revision")
    if relationship_repositories and relationship_repositories != repositories:
        raise ValueError("relationship evidence must use the same source repository as harvest records")
    if relationship_revisions and relationship_revisions != revisions:
        raise ValueError("relationship evidence must use the same source revision as harvest records")

    return ExtractionReceipt(
        receipt_version=RECEIPT_VERSION,
        operation=RECEIPT_OPERATION,
        source_repository=next(iter(repositories)),
        source_revision=next(iter(revisions)),
        record_count=len(materialized),
        manifest_sha256=_manifest_sha256(materialized),
        relationship_count=len(materialized_relationships),
        relationship_manifest_sha256=_relationship_manifest_sha256(materialized_relationships),
        relationship_kinds=tuple(sorted({item.relationship_kind for item in materialized_relationships})),
        resolution_states=tuple(sorted({item.resolution_state.value for item in materialized_relationships})),
        tag_rulesets=tuple(sorted({record.tag_ruleset for record in materialized if record.tag_ruleset is not None})),
        qualification_states=tuple(sorted({record.qualification_state.value for record in materialized})),
        database_schema_version=database_schema_version,
        warnings=tuple(sorted(set(warnings))),
        next_gate=next_gate,
    )


def verify_extraction_receipt(
    receipt: ExtractionReceipt,
    records: Iterable[HarvestRecord],
    *,
    relationships: Iterable[HarvestRelationship] = (),
) -> bool:
    try:
        reproduced = build_extraction_receipt(
            records,
            relationships=relationships,
            warnings=receipt.warnings,
            next_gate=receipt.next_gate,
            database_schema_version=receipt.database_schema_version,
        )
    except ValueError:
        return False
    return reproduced == receipt


def write_extraction_receipt(path: str | Path, receipt: ExtractionReceipt) -> None:
    Path(path).write_text(json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_extraction_receipt(path: str | Path) -> ExtractionReceipt:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExtractionReceipt(
        receipt_version=payload["receipt_version"],
        operation=payload["operation"],
        source_repository=payload["source_repository"],
        source_revision=payload["source_revision"],
        record_count=payload["record_count"],
        manifest_sha256=payload["manifest_sha256"],
        relationship_count=payload.get("relationship_count", 0),
        relationship_manifest_sha256=payload.get("relationship_manifest_sha256", _relationship_manifest_sha256([])),
        relationship_kinds=tuple(payload.get("relationship_kinds", ())),
        resolution_states=tuple(payload.get("resolution_states", ())),
        tag_rulesets=tuple(payload["tag_rulesets"]),
        qualification_states=tuple(payload["qualification_states"]),
        database_schema_version=payload["database_schema_version"],
        warnings=tuple(payload["warnings"]),
        next_gate=payload["next_gate"],
    )


def _manifest_sha256(records: Iterable[HarvestRecord]) -> str:
    entries = [
        {
            "source_repository": record.source_repository,
            "source_revision": record.source_revision,
            "path": record.path,
            "unit_kind": record.unit_kind,
            "unit_identity": record.unit_identity,
            "symbol_name": record.symbol_name,
            "source_sha256": record.source_sha256,
            "representation_sha256": record.representation_sha256,
            "start_byte": record.start_byte,
            "end_byte": record.end_byte,
            "start_row": record.start_row,
            "start_column": record.start_column,
            "end_row": record.end_row,
            "end_column": record.end_column,
            "tags": sorted(set(record.tags)),
            "tag_ruleset": record.tag_ruleset,
            "qualification_state": record.qualification_state.value,
        }
        for record in records
    ]
    entries.sort(key=lambda item: (item["source_repository"], item["source_revision"], item["path"], item["unit_kind"], item["unit_identity"]))
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _relationship_manifest_sha256(relationships: Iterable[HarvestRelationship]) -> str:
    entries = [
        {
            "source_repository": item.source_repository,
            "source_revision": item.source_revision,
            "source_path": item.source_path,
            "source_unit_kind": item.source_unit_kind,
            "source_unit_identity": item.source_unit_identity,
            "relationship_kind": item.relationship_kind,
            "target_path": item.target_path,
            "target_unit_kind": item.target_unit_kind,
            "target_unit_identity": item.target_unit_identity,
            "literal_target": item.literal_target,
            "resolution_state": item.resolution_state.value,
            "start_byte": item.start_byte,
            "end_byte": item.end_byte,
            "start_row": item.start_row,
            "start_column": item.start_column,
            "end_row": item.end_row,
            "end_column": item.end_column,
            "extractor_name": item.extractor_name,
            "extractor_version": item.extractor_version,
        }
        for item in relationships
    ]
    entries.sort(key=lambda item: (
        item["source_repository"], item["source_revision"], item["source_path"], item["source_unit_kind"],
        item["source_unit_identity"], item["relationship_kind"], item["target_path"],
        item["target_unit_identity"], item["literal_target"], item["start_byte"] if item["start_byte"] is not None else -1,
        item["end_byte"] if item["end_byte"] is not None else -1,
    ))
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
