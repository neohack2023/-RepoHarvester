"""Fail-closed validation tests for serialized extraction receipts."""

from __future__ import annotations

import json

import pytest

from repoharvester import HarvestRecord, QualificationState
from repoharvester.receipts import (
    ReceiptValidationError,
    build_extraction_receipt,
    load_extraction_receipt,
    validate_extraction_receipt_payload,
    verify_extraction_receipt,
)


def _record() -> HarvestRecord:
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path="src/example.py",
        unit_kind="file",
        language="Python",
        source_sha256="b" * 64,
        representation_sha256="c" * 64,
        representation="# fixture",
        qualification_state=QualificationState.RAW,
        tags=("language:Python", "role:source"),
        tag_ruleset="path-baseline-v1",
    )


def _payload() -> dict[str, object]:
    return json.loads(json.dumps(build_extraction_receipt([_record()]).to_dict()))


def test_current_receipt_payload_passes_fail_closed_validation(tmp_path) -> None:
    payload = _payload()
    validated = validate_extraction_receipt_payload(payload)
    path = tmp_path / "EXTRACTION_RECEIPT.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_extraction_receipt(path)

    assert validated == payload
    assert json.loads(json.dumps(loaded.to_dict())) == payload
    assert verify_extraction_receipt(loaded, [_record()])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"receipt_version": "repoharvester-extraction-v99"}, "unsupported receipt_version"),
        ({"manifest_sha256": "not-a-digest"}, "manifest_sha256"),
        ({"record_count": True}, "record_count"),
        ({"database_schema_version": 0}, "database_schema_version"),
        ({"warnings": "not-an-array"}, "warnings"),
        ({"operation": "different-operation"}, "operation"),
    ],
)
def test_invalid_current_receipt_fields_fail_closed(mutation, message) -> None:
    payload = _payload()
    payload.update(mutation)

    with pytest.raises(ReceiptValidationError, match=message):
        validate_extraction_receipt_payload(payload)


def test_missing_and_extra_fields_fail_closed() -> None:
    missing = _payload()
    missing.pop("relationship_count")
    with pytest.raises(ReceiptValidationError, match="missing required fields"):
        validate_extraction_receipt_payload(missing)

    extra = _payload()
    extra["untrusted_extension"] = "surprise"
    with pytest.raises(ReceiptValidationError, match="unsupported fields"):
        validate_extraction_receipt_payload(extra)


def test_non_object_and_malformed_json_fail_closed(tmp_path) -> None:
    with pytest.raises(ReceiptValidationError, match="JSON object"):
        validate_extraction_receipt_payload([])

    path = tmp_path / "EXTRACTION_RECEIPT.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ReceiptValidationError, match="unable to read extraction receipt"):
        load_extraction_receipt(path)


def test_v2_receipt_remains_loadable_for_inspection_but_not_current_verification(tmp_path) -> None:
    payload = _payload()
    payload["receipt_version"] = "repoharvester-extraction-v2"
    for field in (
        "relationship_count",
        "relationship_manifest_sha256",
        "relationship_kinds",
        "resolution_states",
    ):
        payload.pop(field)

    path = tmp_path / "EXTRACTION_RECEIPT-v2.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_extraction_receipt(path)

    assert loaded.receipt_version == "repoharvester-extraction-v2"
    assert loaded.relationship_count == 0
    assert loaded.relationship_kinds == ()
    assert not verify_extraction_receipt(loaded, [_record()])
