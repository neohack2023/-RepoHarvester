"""Deterministic evidence-backed qualification primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Iterable

from repoharvester.models import HarvestRecord, HarvestRelationship, QualificationState
from repoharvester.receipts import ExtractionReceipt, verify_extraction_receipt

QUALIFICATION_GATE_ID = "raw-to-candidate-v1"
QUALIFICATION_DECISION_VERSION = "repoharvester-qualification-decision-v1"
QUALIFICATION_RECEIPT_VERSION = "repoharvester-qualification-receipt-v1"


class QualificationDisposition(str, Enum):
    """Disposition emitted by one qualification gate evaluation."""

    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class QualificationDecision:
    """One deterministic decision about a single harvested code unit."""

    decision_version: str
    gate_id: str
    source_repository: str
    source_revision: str
    path: str
    unit_kind: str
    unit_identity: str
    from_state: QualificationState
    target_state: QualificationState
    disposition: QualificationDisposition
    evidence_refs: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    decision_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_version": self.decision_version,
            "gate_id": self.gate_id,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "path": self.path,
            "unit_kind": self.unit_kind,
            "unit_identity": self.unit_identity,
            "from_state": self.from_state.value,
            "target_state": self.target_state.value,
            "disposition": self.disposition.value,
            "evidence_refs": list(self.evidence_refs),
            "blocking_reasons": list(self.blocking_reasons),
            "decision_sha256": self.decision_sha256,
        }


@dataclass(frozen=True)
class QualificationReceipt:
    """Compact receipt binding a qualification gate to deterministic decisions."""

    receipt_version: str
    gate_id: str
    source_repository: str
    source_revision: str
    decision_count: int
    passed_count: int
    blocked_count: int
    decision_manifest_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "gate_id": self.gate_id,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "decision_count": self.decision_count,
            "passed_count": self.passed_count,
            "blocked_count": self.blocked_count,
            "decision_manifest_sha256": self.decision_manifest_sha256,
        }


def evaluate_raw_to_candidate(
    record: HarvestRecord,
    records: Iterable[HarvestRecord],
    receipt: ExtractionReceipt,
    *,
    relationships: Iterable[HarvestRelationship] = (),
    validation_references: Iterable[str] = (),
) -> QualificationDecision:
    """Evaluate the first bounded RAW -> CANDIDATE gate for one code unit.

    This gate proves evidence completeness only. It does not assert code quality,
    security, dependency safety, legal compatibility, intended-use compatibility,
    or reusability.
    """
    materialized_records = list(records)
    materialized_relationships = list(relationships)
    validations = tuple(sorted({item.strip() for item in validation_references if item.strip()}))
    evidence_refs: list[str] = []
    blockers: list[str] = []

    if record not in materialized_records:
        blockers.append("subject record is not present in the evaluated harvest set")
    if record.qualification_state != QualificationState.RAW:
        blockers.append("subject state is not RAW")
    if not record.unit_kind.startswith("symbol:"):
        blockers.append("gate admits code-unit symbols only")

    receipt_matches = verify_extraction_receipt(
        receipt,
        materialized_records,
        relationships=materialized_relationships,
    )
    if not receipt_matches:
        blockers.append("current extraction receipt does not reproduce from supplied evidence")
    elif receipt.source_repository != record.source_repository or receipt.source_revision != record.source_revision:
        blockers.append("receipt provenance does not match subject provenance")
    else:
        evidence_refs.extend(
            (
                f"source-revision:git:{record.source_revision}",
                f"extraction-receipt:sha256:{receipt.manifest_sha256}",
            )
        )

    license_records = [
        item
        for item in materialized_records
        if item.source_repository == record.source_repository
        and item.source_revision == record.source_revision
        and item.unit_kind == "evidence:repository-license"
    ]
    if len(license_records) != 1:
        blockers.append("exactly one repository-license evidence record is required")
    else:
        license_record = license_records[0]
        spdx_tags = sorted(tag for tag in license_record.tags if tag.startswith("license:spdx:"))
        if len(spdx_tags) != 1 or spdx_tags[0] == "license:spdx:UNKNOWN":
            blockers.append("repository license evidence is missing or ambiguous")
        else:
            evidence_refs.append(
                f"repository-license:{license_record.path}:sha256:{license_record.representation_sha256}"
            )

    dependency_records = [
        item
        for item in materialized_records
        if item.source_repository == record.source_repository
        and item.source_revision == record.source_revision
        and item.unit_kind == "evidence:declared-dependency"
    ]
    if not dependency_records:
        blockers.append("declared dependency evidence is required for this gate")
    else:
        for dependency in sorted(
            dependency_records,
            key=lambda item: (item.symbol_name or "", item.unit_identity),
        ):
            evidence_refs.append(
                "declared-dependency:"
                f"{dependency.symbol_name or dependency.unit_identity}:"
                f"sha256:{dependency.representation_sha256}"
            )

    if not validations:
        blockers.append("at least one explicit validation reference is required")
    else:
        evidence_refs.extend(f"validation:{item}" for item in validations)

    disposition = QualificationDisposition.PASS if not blockers else QualificationDisposition.BLOCKED
    evidence_tuple = tuple(sorted(set(evidence_refs)))
    blocker_tuple = tuple(sorted(set(blockers)))
    decision_payload = {
        "decision_version": QUALIFICATION_DECISION_VERSION,
        "gate_id": QUALIFICATION_GATE_ID,
        "source_repository": record.source_repository,
        "source_revision": record.source_revision,
        "path": record.path,
        "unit_kind": record.unit_kind,
        "unit_identity": record.unit_identity,
        "from_state": record.qualification_state.value,
        "target_state": QualificationState.CANDIDATE.value,
        "disposition": disposition.value,
        "evidence_refs": list(evidence_tuple),
        "blocking_reasons": list(blocker_tuple),
    }
    decision_sha256 = hashlib.sha256(_canonical_json(decision_payload).encode("utf-8")).hexdigest()
    return QualificationDecision(
        decision_version=QUALIFICATION_DECISION_VERSION,
        gate_id=QUALIFICATION_GATE_ID,
        source_repository=record.source_repository,
        source_revision=record.source_revision,
        path=record.path,
        unit_kind=record.unit_kind,
        unit_identity=record.unit_identity,
        from_state=record.qualification_state,
        target_state=QualificationState.CANDIDATE,
        disposition=disposition,
        evidence_refs=evidence_tuple,
        blocking_reasons=blocker_tuple,
        decision_sha256=decision_sha256,
    )


def apply_candidate_qualification(record: HarvestRecord, decision: QualificationDecision) -> HarvestRecord:
    """Apply a matching PASS decision without changing source evidence or tags."""
    identity = (
        record.source_repository,
        record.source_revision,
        record.path,
        record.unit_kind,
        record.unit_identity,
    )
    decision_identity = (
        decision.source_repository,
        decision.source_revision,
        decision.path,
        decision.unit_kind,
        decision.unit_identity,
    )
    if identity != decision_identity:
        raise ValueError("qualification decision does not match subject identity")
    if record.qualification_state != decision.from_state:
        raise ValueError("qualification decision source state does not match subject state")
    if decision.disposition != QualificationDisposition.PASS or decision.blocking_reasons:
        raise ValueError("blocked qualification decisions cannot change lifecycle state")
    if decision.target_state != QualificationState.CANDIDATE:
        raise ValueError("raw-to-candidate gate can only target CANDIDATE")
    return replace(record, qualification_state=QualificationState.CANDIDATE)


def build_qualification_receipt(decisions: Iterable[QualificationDecision]) -> QualificationReceipt:
    """Bind one gate execution to its exact deterministic decisions."""
    materialized = list(decisions)
    if not materialized:
        raise ValueError("qualification receipts require at least one decision")
    repositories = {item.source_repository for item in materialized}
    revisions = {item.source_revision for item in materialized}
    gates = {item.gate_id for item in materialized}
    if len(repositories) != 1 or len(revisions) != 1 or gates != {QUALIFICATION_GATE_ID}:
        raise ValueError("qualification receipt decisions must share one repository, revision, and gate")
    decision_hashes = [item.decision_sha256 for item in sorted(materialized, key=_decision_sort_key)]
    manifest = hashlib.sha256(_canonical_json(decision_hashes).encode("utf-8")).hexdigest()
    passed = sum(item.disposition == QualificationDisposition.PASS for item in materialized)
    blocked = len(materialized) - passed
    return QualificationReceipt(
        receipt_version=QUALIFICATION_RECEIPT_VERSION,
        gate_id=QUALIFICATION_GATE_ID,
        source_repository=next(iter(repositories)),
        source_revision=next(iter(revisions)),
        decision_count=len(materialized),
        passed_count=passed,
        blocked_count=blocked,
        decision_manifest_sha256=manifest,
    )


def verify_qualification_receipt(
    receipt: QualificationReceipt,
    decisions: Iterable[QualificationDecision],
) -> bool:
    """Reproduce one qualification receipt from its decision set."""
    try:
        return build_qualification_receipt(decisions) == receipt
    except ValueError:
        return False


def write_qualification_decisions(path: str | Path, decisions: Iterable[QualificationDecision]) -> None:
    """Write deterministic qualification decisions for inspection and audit."""
    payload = [item.to_dict() for item in sorted(decisions, key=_decision_sort_key)]
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_qualification_receipt(path: str | Path, receipt: QualificationReceipt) -> None:
    """Write one compact qualification receipt."""
    Path(path).write_text(json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _decision_sort_key(item: QualificationDecision) -> tuple[str, str, str]:
    return (item.path, item.unit_kind, item.unit_identity)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
