"""Compact deterministic receipts for provenance-backed harvest operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from repoharvester.models import HarvestRecord, HarvestRelationship
from repoharvester.storage import SCHEMA_VERSION

RECEIPT_VERSION = "repoharvester-extraction-v3"
RECEIPT_OPERATION = "harvest-store"
DEFAULT_NEXT_GATE = "external-repository acceptance run"
SUPPORTED_RECEIPT_VERSIONS = frozenset(
    {
        "repoharvester-extraction-v1",
        "repoharvester-extraction-v2",
        RECEIPT_VERSION,
    }
)

_BASE_RECEIPT_FIELDS = frozenset(
    {
        "receipt_version",
        "operation",
        "source_repository",
        "source_revision",
        "record_count",
        "manifest_sha256",
        "tag_rulesets",
        "qualification_states",
        "database_schema_version",
        "warnings",
        "next_gate",
    }
)
_RELATIONSHIP_RECEIPT_FIELDS = frozenset(
    {
        "relationship_count",
        "relationship_manifest_sha256",
        "relationship_kinds",
        "resolution_states",
    }
)


class ReceiptValidationError(ValueError):
    """Raised when serialized receipt evidence does not match a supported contract."""


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
    if receipt.receipt_version != RECEIPT_VERSION or receipt.operation != RECEIPT_OPERATION:
        return False
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


def validate_extraction_receipt_payload(payload: object) -> Mapping[str, object]:
    """Validate one serialized receipt payload before constructing trusted receipt evidence.

    Versions 1 and 2 remain loadable for inspection, but only the current version can pass
    ``verify_extraction_receipt`` because reproduction uses the current evidence contract.
    """
    if not isinstance(payload, dict):
        raise ReceiptValidationError("extraction receipt must be a JSON object")

    version = payload.get("receipt_version")
    if not isinstance(version, str) or version not in SUPPORTED_RECEIPT_VERSIONS:
        raise ReceiptValidationError(f"unsupported receipt_version: {version!r}")

    expected_fields = _BASE_RECEIPT_FIELDS
    if version == RECEIPT_VERSION:
        expected_fields = expected_fields | _RELATIONSHIP_RECEIPT_FIELDS

    actual_fields = frozenset(payload)
    missing = sorted(expected_fields - actual_fields)
    extra = sorted(actual_fields - expected_fields)
    if missing:
        raise ReceiptValidationError(f"receipt is missing required fields: {', '.join(missing)}")
    if extra:
        raise ReceiptValidationError(f"receipt contains unsupported fields: {', '.join(extra)}")

    _require_exact_string(payload, "operation", RECEIPT_OPERATION)
    _require_non_empty_string(payload, "source_repository")
    _require_non_empty_string(payload, "source_revision")
    _require_non_negative_int(payload, "record_count")
    _require_sha256(payload, "manifest_sha256")
    _require_positive_int(payload, "database_schema_version")
    _require_string_array(payload, "tag_rulesets")
    _require_string_array(payload, "qualification_states")
    _require_string_array(payload, "warnings")
    _require_non_empty_string(payload, "next_gate")

    if version == RECEIPT_VERSION:
        _require_non_negative_int(payload, "relationship_count")
        _require_sha256(payload, "relationship_manifest_sha256")
        _require_string_array(payload, "relationship_kinds")
        _require_string_array(payload, "resolution_states")

    return payload


def load_extraction_receipt(path: str | Path) -> ExtractionReceipt:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError(f"unable to read extraction receipt: {exc}") from exc

    validated = validate_extraction_receipt_payload(payload)
    version = validated["receipt_version"]
    assert isinstance(version, str)

    empty_relationship_manifest = _relationship_manifest_sha256([])
    return ExtractionReceipt(
        receipt_version=version,
        operation=_string_value(validated, "operation"),
        source_repository=_string_value(validated, "source_repository"),
        source_revision=_string_value(validated, "source_revision"),
        record_count=_int_value(validated, "record_count"),
        manifest_sha256=_string_value(validated, "manifest_sha256"),
        relationship_count=_optional_int_value(validated, "relationship_count", 0),
        relationship_manifest_sha256=_optional_string_value(
            validated,
            "relationship_manifest_sha256",
            empty_relationship_manifest,
        ),
        relationship_kinds=tuple(_optional_string_array(validated, "relationship_kinds")),
        resolution_states=tuple(_optional_string_array(validated, "resolution_states")),
        tag_rulesets=tuple(_string_array_value(validated, "tag_rulesets")),
        qualification_states=tuple(_string_array_value(validated, "qualification_states")),
        database_schema_version=_int_value(validated, "database_schema_version"),
        warnings=tuple(_string_array_value(validated, "warnings")),
        next_gate=_string_value(validated, "next_gate"),
    )


def _require_exact_string(payload: Mapping[str, object], field: str, expected: str) -> None:
    value = payload.get(field)
    if value != expected or not isinstance(value, str):
        raise ReceiptValidationError(f"{field} must equal {expected!r}")


def _require_non_empty_string(payload: Mapping[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ReceiptValidationError(f"{field} must be a non-empty string")


def _require_non_negative_int(payload: Mapping[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReceiptValidationError(f"{field} must be a non-negative integer")


def _require_positive_int(payload: Mapping[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ReceiptValidationError(f"{field} must be a positive integer")


def _require_sha256(payload: Mapping[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ReceiptValidationError(f"{field} must be a lowercase SHA-256 hex digest")


def _require_string_array(payload: Mapping[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ReceiptValidationError(f"{field} must be an array of strings")


def _string_value(payload: Mapping[str, object], field: str) -> str:
    value = payload[field]
    assert isinstance(value, str)
    return value


def _int_value(payload: Mapping[str, object], field: str) -> int:
    value = payload[field]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _string_array_value(payload: Mapping[str, object], field: str) -> list[str]:
    value = payload[field]
    assert isinstance(value, list)
    return [item for item in value if isinstance(item, str)]


def _optional_int_value(payload: Mapping[str, object], field: str, default: int) -> int:
    value = payload.get(field, default)
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _optional_string_value(payload: Mapping[str, object], field: str, default: str) -> str:
    value = payload.get(field, default)
    assert isinstance(value, str)
    return value


def _optional_string_array(payload: Mapping[str, object], field: str) -> list[str]:
    value = payload.get(field, [])
    assert isinstance(value, list)
    return [item for item in value if isinstance(item, str)]


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
