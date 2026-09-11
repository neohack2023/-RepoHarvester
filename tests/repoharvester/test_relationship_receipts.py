"""Tests for relationship-bound extraction receipts."""

from __future__ import annotations

from repoharvester import HarvestRecord, HarvestRelationship, ResolutionState
from repoharvester.receipts import build_extraction_receipt, verify_extraction_receipt


def _record() -> HarvestRecord:
    return HarvestRecord(
        source_repository="repo",
        source_revision="a" * 40,
        path="src/a.ts",
        unit_kind="file",
        language="TypeScript",
        source_sha256="b" * 64,
        representation_sha256="c" * 64,
        representation="import './b';\n",
    )


def _relationship(**overrides) -> HarvestRelationship:
    values = {
        "source_repository": "repo",
        "source_revision": "a" * 40,
        "source_path": "src/a.ts",
        "source_unit_kind": "file",
        "source_unit_identity": "",
        "relationship_kind": "imports",
        "target_path": "src/b.ts",
        "target_unit_kind": "file",
        "target_unit_identity": "",
        "literal_target": "'./b'",
        "resolution_state": ResolutionState.EXACT,
        "start_byte": 0,
        "end_byte": 13,
        "start_row": 0,
        "start_column": 0,
        "end_row": 0,
        "end_column": 13,
        "extractor_name": "tree-sitter-typescript",
        "extractor_version": "0.21.2",
    }
    values.update(overrides)
    return HarvestRelationship(**values)


def test_receipt_binds_relationship_manifest_and_detects_drift() -> None:
    record = _record()
    relationship = _relationship()
    receipt = build_extraction_receipt([record], relationships=[relationship])

    assert receipt.relationship_count == 1
    assert receipt.relationship_kinds == ("imports",)
    assert receipt.resolution_states == ("EXACT",)
    assert verify_extraction_receipt(receipt, [record], relationships=[relationship])
    assert not verify_extraction_receipt(
        receipt,
        [record],
        relationships=[_relationship(literal_target="'./changed'")],
    )
