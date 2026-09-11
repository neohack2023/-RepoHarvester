from __future__ import annotations

from dataclasses import replace

import pytest

from repoharvester import (
    HarvestRecord,
    QualificationDisposition,
    QualificationState,
    apply_candidate_qualification,
    build_extraction_receipt,
    build_qualification_receipt,
    evaluate_raw_to_candidate,
    verify_qualification_receipt,
)

REPOSITORY = "https://example.com/repo.git"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def _records() -> list[HarvestRecord]:
    return [
        HarvestRecord(
            source_repository=REPOSITORY,
            source_revision=REVISION,
            path="src/example.ts",
            unit_kind="symbol:function",
            language="TypeScript",
            source_sha256="1" * 64,
            representation_sha256="2" * 64,
            representation="export function example() {}",
            unit_identity="typescript:function:example:0:28",
            symbol_name="example",
            tags=("unit:symbol", "symbol:function"),
            tag_ruleset="typescript-symbol-v1",
        ),
        HarvestRecord(
            source_repository=REPOSITORY,
            source_revision=REVISION,
            path="LICENSE",
            unit_kind="evidence:repository-license",
            language=None,
            source_sha256="3" * 64,
            representation_sha256="4" * 64,
            representation="MIT License",
            unit_identity="repository-license:LICENSE",
            tags=("evidence:repository-license", "license:spdx:MIT"),
            tag_ruleset="repository-license-v1",
        ),
        HarvestRecord(
            source_repository=REPOSITORY,
            source_revision=REVISION,
            path="package.json",
            unit_kind="evidence:declared-dependency",
            language="JSON",
            source_sha256="5" * 64,
            representation_sha256="6" * 64,
            representation="^1.2.3",
            unit_identity="package-json:dependencies:example:^1.2.3",
            symbol_name="example-package",
            tags=(
                "evidence:declared-dependency",
                "dependency:name:example-package",
                "dependency:scope:runtime",
            ),
            tag_ruleset="package-json-dependencies-v1",
        ),
    ]


def test_raw_symbol_passes_candidate_gate_with_complete_evidence() -> None:
    records = _records()
    receipt = build_extraction_receipt(records, next_gate="QUALIFICATION_GATE_01")

    decision = evaluate_raw_to_candidate(
        records[0],
        records,
        receipt,
        validation_references=("external-acceptance:pinned-source-clean-roundtrip-v1",),
    )

    assert decision.disposition == QualificationDisposition.PASS
    assert decision.blocking_reasons == ()
    assert decision.target_state == QualificationState.CANDIDATE
    assert any(item.startswith("extraction-receipt:sha256:") for item in decision.evidence_refs)
    assert any(item.startswith("repository-license:LICENSE:sha256:") for item in decision.evidence_refs)
    assert any(item.startswith("declared-dependency:example-package:sha256:") for item in decision.evidence_refs)
    assert "validation:external-acceptance:pinned-source-clean-roundtrip-v1" in decision.evidence_refs

    promoted = apply_candidate_qualification(records[0], decision)
    assert promoted.qualification_state == QualificationState.CANDIDATE
    assert promoted.source_sha256 == records[0].source_sha256
    assert promoted.representation_sha256 == records[0].representation_sha256
    assert promoted.tags == records[0].tags

    qualification_receipt = build_qualification_receipt([decision])
    assert qualification_receipt.passed_count == 1
    assert qualification_receipt.blocked_count == 0
    assert verify_qualification_receipt(qualification_receipt, [decision])


def test_candidate_gate_blocks_unknown_repository_license() -> None:
    records = _records()
    records[1] = replace(records[1], tags=("evidence:repository-license", "license:spdx:UNKNOWN"))
    receipt = build_extraction_receipt(records, next_gate="QUALIFICATION_GATE_01")

    decision = evaluate_raw_to_candidate(
        records[0],
        records,
        receipt,
        validation_references=("external-acceptance:test",),
    )

    assert decision.disposition == QualificationDisposition.BLOCKED
    assert "repository license evidence is missing or ambiguous" in decision.blocking_reasons
    with pytest.raises(ValueError, match="blocked qualification decisions"):
        apply_candidate_qualification(records[0], decision)


def test_candidate_gate_blocks_missing_dependency_evidence() -> None:
    records = _records()[:2]
    receipt = build_extraction_receipt(records, next_gate="QUALIFICATION_GATE_01")

    decision = evaluate_raw_to_candidate(
        records[0],
        records,
        receipt,
        validation_references=("external-acceptance:test",),
    )

    assert decision.disposition == QualificationDisposition.BLOCKED
    assert "declared dependency evidence is required for this gate" in decision.blocking_reasons


def test_candidate_gate_blocks_missing_validation_reference() -> None:
    records = _records()
    receipt = build_extraction_receipt(records, next_gate="QUALIFICATION_GATE_01")

    decision = evaluate_raw_to_candidate(records[0], records, receipt)

    assert decision.disposition == QualificationDisposition.BLOCKED
    assert "at least one explicit validation reference is required" in decision.blocking_reasons


def test_candidate_gate_blocks_non_reproducible_receipt() -> None:
    records = _records()
    receipt = build_extraction_receipt(records, next_gate="QUALIFICATION_GATE_01")
    changed_records = list(records)
    changed_records[2] = replace(changed_records[2], representation="^9.9.9")

    decision = evaluate_raw_to_candidate(
        changed_records[0],
        changed_records,
        receipt,
        validation_references=("external-acceptance:test",),
    )

    assert decision.disposition == QualificationDisposition.BLOCKED
    assert "current extraction receipt does not reproduce from supplied evidence" in decision.blocking_reasons


def test_candidate_gate_rejects_file_level_subject() -> None:
    records = _records()
    file_record = replace(
        records[0],
        unit_kind="file",
        unit_identity="",
        symbol_name=None,
    )
    evaluated = [file_record, *records[1:]]
    receipt = build_extraction_receipt(evaluated, next_gate="QUALIFICATION_GATE_01")

    decision = evaluate_raw_to_candidate(
        file_record,
        evaluated,
        receipt,
        validation_references=("external-acceptance:test",),
    )

    assert decision.disposition == QualificationDisposition.BLOCKED
    assert "gate admits code-unit symbols only" in decision.blocking_reasons
