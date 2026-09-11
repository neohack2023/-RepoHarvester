"""Compact deterministic receipts for provenance-backed harvest operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from repoharvester.models import HarvestRecord
from repoharvester.storage import SCHEMA_VERSION

RECEIPT_VERSION = "repoharvester-extraction-v2"
RECEIPT_OPERATION = "harvest-store"
DEFAULT_NEXT_GATE = "external-repository acceptance run"


@dataclass(frozen=True)
class ExtractionReceipt:
    """Compact evidence binding one harvested revision to stored record identities."""

    receipt_version: str
    operation: str
    source_repository: str
    source_revision: str
    record_count: int
    manifest_sha256: str
    tag_rulesets: tuple[str, ...]
    qualification_states: tuple[str, ...]
    database_schema_version: int
    warnings: tuple[str, ...]
    next_gate: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation with stable field names."""
        return asdict(self)


def build_extraction_receipt(
    records: Iterable[HarvestRecord],
    *,
    warnings: Iterable[str] = (),
    next_gate: str = DEFAULT_NEXT_GATE,
    database_schema_version: int = SCHEMA_VERSION,
) -> ExtractionReceipt:
    """Build a deterministic receipt for records from exactly one repository revision."""
    materialized = list(records)
    if not materialized:
        message = "extraction receipts require at least one harvest record"
        raise ValueError(message)

    repositories = {record.source_repository for record in materialized}
    revisions = {record.source_revision for record in materialized}
    if len(repositories) != 1 or len(revisions) != 1:
        message = "extraction receipts require exactly one source repository and revision"
        raise ValueError(message)

    tag_rulesets = tuple(
        sorted({record.tag_ruleset for record in materialized if record.tag_ruleset is not None})
    )
    qualification_states = tuple(
        sorted({record.qualification_state.value for record in materialized})
    )
    return ExtractionReceipt(
        receipt_version=RECEIPT_VERSION,
        operation=RECEIPT_OPERATION,
        source_repository=next(iter(repositories)),
        source_revision=next(iter(revisions)),
        record_count=len(materialized),
        manifest_sha256=_manifest_sha256(materialized),
        tag_rulesets=tag_rulesets,
        qualification_states=qualification_states,
        database_schema_version=database_schema_version,
        warnings=tuple(sorted(set(warnings))),
        next_gate=next_gate,
    )


def verify_extraction_receipt(receipt: ExtractionReceipt, records: Iterable[HarvestRecord]) -> bool:
    """Verify that records reproduce the evidence-bound fields of a receipt exactly."""
    try:
        reproduced = build_extraction_receipt(
            records,
            warnings=receipt.warnings,
            next_gate=receipt.next_gate,
            database_schema_version=receipt.database_schema_version,
        )
    except ValueError:
        return False
    return reproduced == receipt


def write_extraction_receipt(path: str | Path, receipt: ExtractionReceipt) -> None:
    """Write canonical pretty JSON suitable for durable evidence storage."""
    output = Path(path)
    output.write_text(
        json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_extraction_receipt(path: str | Path) -> ExtractionReceipt:
    """Load a receipt previously written by :func:`write_extraction_receipt`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExtractionReceipt(
        receipt_version=payload["receipt_version"],
        operation=payload["operation"],
        source_repository=payload["source_repository"],
        source_revision=payload["source_revision"],
        record_count=payload["record_count"],
        manifest_sha256=payload["manifest_sha256"],
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
    entries.sort(
        key=lambda item: (
            item["source_repository"],
            item["source_revision"],
            item["path"],
            item["unit_kind"],
            item["unit_identity"],
        )
    )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
