from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Callable, Iterable, Mapping, Sequence


AUTHORITY_EFFECT = "NONE"
PROMOTION_STATE = "CANDIDATE_ONLY"


class EvaluationTier(str, Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"


class MaturityStage(str, Enum):
    RECALL = "RECALL"
    RECOGNITION = "RECOGNITION"
    REFLECTION = "REFLECTION"
    TRANSFER = "TRANSFER"
    COMPOSITION = "COMPOSITION"
    ADAPTATION = "ADAPTATION"
    METACOGNITIVE_CONTROL = "METACOGNITIVE_CONTROL"


@dataclass(frozen=True)
class ProcedureSpec:
    branch_scope: str
    name: str
    version: str
    trigger_conditions: tuple[str, ...]
    input_schema: tuple[str, ...]
    output_schema: tuple[str, ...]
    implementation_ref: str
    preconditions: tuple[str, ...] = ()
    known_failures: tuple[str, ...] = ()
    source_evidence_refs: tuple[str, ...] = ()
    rollback_ref: str = ""

    @property
    def procedure_id(self) -> str:
        payload = {
            "branch_scope": self.branch_scope,
            "name": self.name,
            "version": self.version,
            "trigger_conditions": self.trigger_conditions,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "implementation_ref": self.implementation_ref,
            "preconditions": self.preconditions,
            "known_failures": self.known_failures,
            "source_evidence_refs": self.source_evidence_refs,
            "rollback_ref": self.rollback_ref,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return f"procedure:{digest[:24]}"


@dataclass(frozen=True)
class EvaluationFixture:
    fixture_id: str
    tier: EvaluationTier
    payload: Mapping[str, object]
    expected: object


@dataclass(frozen=True)
class FixtureResult:
    fixture_id: str
    tier: EvaluationTier
    passed: bool
    actual: object
    expected: object


@dataclass(frozen=True)
class EvaluationReport:
    procedure_id: str
    results: tuple[FixtureResult, ...]
    canary_required: bool = True
    authority_effect: str = AUTHORITY_EFFECT
    promotion_state: str = PROMOTION_STATE

    @property
    def passed_by_tier(self) -> dict[EvaluationTier, bool]:
        grouped: dict[EvaluationTier, list[bool]] = {}
        for result in self.results:
            grouped.setdefault(result.tier, []).append(result.passed)
        return {tier: bool(values) and all(values) for tier, values in grouped.items()}

    @property
    def validated_for_transfer(self) -> bool:
        status = self.passed_by_tier
        return all(status.get(tier, False) for tier in (
            EvaluationTier.T0,
            EvaluationTier.T1,
            EvaluationTier.T2,
            EvaluationTier.T3,
        ))

    @property
    def adversarially_robust(self) -> bool:
        return self.validated_for_transfer and self.passed_by_tier.get(EvaluationTier.T4, False)


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    branch_scope: str
    description: str
    procedure_ids: tuple[str, ...]
    known_tasks: tuple[str, ...]
    known_failure_modes: tuple[str, ...]
    maturity_stage: MaturityStage
    recent_eval_profile: tuple[tuple[str, bool], ...]
    transfer_fixture_ids: tuple[str, ...]
    authority_effect: str = AUTHORITY_EFFECT
    promotion_state: str = PROMOTION_STATE


class CapabilityGraph:
    def __init__(self) -> None:
        self._records: dict[str, CapabilityRecord] = {}

    def upsert_from_evaluation(
        self,
        *,
        capability_key: str,
        description: str,
        procedure: ProcedureSpec,
        report: EvaluationReport,
        known_tasks: Iterable[str] = (),
        known_failure_modes: Iterable[str] = (),
    ) -> CapabilityRecord:
        if report.procedure_id != procedure.procedure_id:
            raise ValueError("evaluation report does not belong to procedure")

        maturity = maturity_from_report(report)
        transfer_ids = tuple(
            result.fixture_id
            for result in report.results
            if result.tier == EvaluationTier.T3 and result.passed
        )
        eval_profile = tuple(
            (tier.value, passed)
            for tier, passed in sorted(report.passed_by_tier.items(), key=lambda item: item[0].value)
        )
        capability_id = _stable_id(
            "capability",
            {
                "capability_key": capability_key,
                "branch_scope": procedure.branch_scope,
            },
        )
        record = CapabilityRecord(
            capability_id=capability_id,
            branch_scope=procedure.branch_scope,
            description=description,
            procedure_ids=(procedure.procedure_id,),
            known_tasks=tuple(sorted(set(known_tasks))),
            known_failure_modes=tuple(sorted(set(known_failure_modes))),
            maturity_stage=maturity,
            recent_eval_profile=eval_profile,
            transfer_fixture_ids=transfer_ids,
        )
        self._records[capability_id] = record
        return record

    def get(self, capability_id: str) -> CapabilityRecord:
        return self._records[capability_id]

    def all(self) -> tuple[CapabilityRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


def consolidate_procedure(
    *,
    branch_scope: str,
    name: str,
    version: str,
    trigger_conditions: Sequence[str],
    input_schema: Sequence[str],
    output_schema: Sequence[str],
    implementation_ref: str,
    source_evidence_refs: Sequence[str],
    preconditions: Sequence[str] = (),
    known_failures: Sequence[str] = (),
    rollback_ref: str = "",
) -> ProcedureSpec:
    if not branch_scope.strip():
        raise ValueError("branch_scope is required")
    if not name.strip() or not version.strip() or not implementation_ref.strip():
        raise ValueError("name, version, and implementation_ref are required")
    if not trigger_conditions or not input_schema or not output_schema:
        raise ValueError("procedure contract must declare triggers, inputs, and outputs")
    if not source_evidence_refs or any(not ref.strip() for ref in source_evidence_refs):
        raise ValueError("source evidence is required and must be addressable")

    return ProcedureSpec(
        branch_scope=branch_scope.strip(),
        name=name.strip(),
        version=version.strip(),
        trigger_conditions=tuple(trigger_conditions),
        input_schema=tuple(input_schema),
        output_schema=tuple(output_schema),
        implementation_ref=implementation_ref.strip(),
        preconditions=tuple(preconditions),
        known_failures=tuple(known_failures),
        source_evidence_refs=tuple(sorted(set(source_evidence_refs))),
        rollback_ref=rollback_ref.strip(),
    )


def evaluate_procedure(
    procedure: ProcedureSpec,
    fixtures: Sequence[EvaluationFixture],
    executor: Callable[[Mapping[str, object]], object],
) -> EvaluationReport:
    if not fixtures:
        raise ValueError("evaluation requires fixtures")

    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("fixture ids must be unique")

    tiers = {fixture.tier for fixture in fixtures}
    required = {EvaluationTier.T0, EvaluationTier.T1, EvaluationTier.T2, EvaluationTier.T3}
    missing = required - tiers
    if missing:
        raise ValueError(f"evaluation missing required tiers: {','.join(sorted(t.value for t in missing))}")

    training_ids = {
        fixture.fixture_id
        for fixture in fixtures
        if fixture.tier in {EvaluationTier.T1, EvaluationTier.T2}
    }
    holdout_ids = {fixture.fixture_id for fixture in fixtures if fixture.tier == EvaluationTier.T3}
    if training_ids & holdout_ids:
        raise ValueError("held-out fixtures must be disjoint from train/dev fixture identities")

    results: list[FixtureResult] = []
    t0_failed = False
    for fixture in sorted(fixtures, key=lambda item: (item.tier.value, item.fixture_id)):
        if t0_failed and fixture.tier != EvaluationTier.T0:
            results.append(
                FixtureResult(
                    fixture_id=fixture.fixture_id,
                    tier=fixture.tier,
                    passed=False,
                    actual="SKIPPED_AFTER_T0_FAILURE",
                    expected=fixture.expected,
                )
            )
            continue
        actual = executor(fixture.payload)
        passed = actual == fixture.expected
        results.append(
            FixtureResult(
                fixture_id=fixture.fixture_id,
                tier=fixture.tier,
                passed=passed,
                actual=actual,
                expected=fixture.expected,
            )
        )
        if fixture.tier == EvaluationTier.T0 and not passed:
            t0_failed = True

    return EvaluationReport(procedure_id=procedure.procedure_id, results=tuple(results))


def maturity_from_report(report: EvaluationReport) -> MaturityStage:
    status = report.passed_by_tier
    if all(status.get(tier, False) for tier in (EvaluationTier.T0, EvaluationTier.T1, EvaluationTier.T2, EvaluationTier.T3)):
        return MaturityStage.TRANSFER
    if all(status.get(tier, False) for tier in (EvaluationTier.T0, EvaluationTier.T1, EvaluationTier.T2)):
        return MaturityStage.REFLECTION
    if all(status.get(tier, False) for tier in (EvaluationTier.T0, EvaluationTier.T1)):
        return MaturityStage.RECOGNITION
    return MaturityStage.RECALL


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{prefix}:{digest[:24]}"
