#!/usr/bin/env python3
"""Build authority-neutral reflection candidates from DevOS CI failure packets.

This module is the CI evidence adapter. Source validation and CI-specific
routing stay here; shared hypothesis semantics live in ``reflection_core``.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence

from tools.reflection_core import (
    build_reflection_core,
    canonical_digest,
    required_text,
    string_list,
)

FAILURE_SCHEMA = "repoharvester-ci-failure/v1"
SIGNAL_NORMALIZATION_VERSION = "repoharvester-ci-signal/v1"
REFLECTION_SCHEMA = "repoharvester-reflection-candidate/v1"


class FailureDomain(str, Enum):
    CODE = "CODE"
    TEST = "TEST"
    RUNTIME = "RUNTIME"
    ENVIRONMENT = "ENVIRONMENT"
    RETRIEVAL = "RETRIEVAL"
    TOOL_CONTRACT = "TOOL_CONTRACT"
    INSTRUCTION = "INSTRUCTION"
    UNKNOWN = "UNKNOWN"


class RoutingDisposition(str, Enum):
    COMPONENT_DEBUG_REQUIRED = "COMPONENT_DEBUG_REQUIRED"
    INTERVENTION_REQUIRED = "INTERVENTION_REQUIRED"
    NEEDS_CLASSIFICATION = "NEEDS_CLASSIFICATION"


NON_INSTRUCTION_DOMAINS = {
    FailureDomain.CODE,
    FailureDomain.TEST,
    FailureDomain.RUNTIME,
    FailureDomain.ENVIRONMENT,
    FailureDomain.RETRIEVAL,
    FailureDomain.TOOL_CONTRACT,
}


@dataclass(frozen=True)
class ReflectionCandidate:
    schema: str
    reflection_id: str
    branch_key: str
    source_packet_digest: str
    source_failure_signature: str
    source_observation_root: str
    source_signal_normalization_version: str
    source_subject_kind: str
    tested_sha: str
    change_head_sha: str
    base_sha: str | None
    gate: str
    observed_failure: str
    failure_domain: str
    classification_evidence_refs: tuple[str, ...]
    routing_disposition: str
    next_gate: str
    expected_behavior: str
    mechanism_hypothesis: str
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    predicted_consequence: str
    required_disconfirmation_test: str
    proposed_scope: str
    authority_effect: str = "NONE"
    promotion_state: str = "CANDIDATE_ONLY"


def validate_failure_packet(packet: Mapping[str, object]) -> None:
    if packet.get("schema") != FAILURE_SCHEMA:
        raise ValueError(f"source packet schema must be {FAILURE_SCHEMA}")
    if packet.get("status") != "FAILED":
        raise ValueError("reflection requires a FAILED source packet")
    if packet.get("authority_effect") != "NONE":
        raise ValueError("source packet must have authority_effect NONE")
    if packet.get("signal_normalization_version") != SIGNAL_NORMALIZATION_VERSION:
        raise ValueError(
            "source packet signal_normalization_version must be "
            f"{SIGNAL_NORMALIZATION_VERSION}"
        )
    for key in ("gate", "signature", "observation_root", "normalized_signal"):
        required_text(packet, key)
    subject = packet.get("subject")
    if not isinstance(subject, dict):
        raise ValueError("source packet subject must be an object")
    if subject.get("identity_state") != "COMPLETE":
        raise ValueError("source packet subject identity must be COMPLETE")
    for key in ("kind", "tested_sha", "change_head_sha"):
        required_text(subject, key)


def packet_digest(packet: Mapping[str, object]) -> str:
    return canonical_digest(packet)


def route_failure_domain(domain: FailureDomain) -> tuple[RoutingDisposition, str]:
    if domain in NON_INSTRUCTION_DOMAINS:
        return RoutingDisposition.COMPONENT_DEBUG_REQUIRED, "EXISTING_HARNESS_OR_COMPONENT_DEBUG"
    if domain == FailureDomain.INSTRUCTION:
        return RoutingDisposition.INTERVENTION_REQUIRED, "FAILURE_INTERVENTION_ATTRIBUTION"
    return RoutingDisposition.NEEDS_CLASSIFICATION, "CLASSIFY_FAILURE_DOMAIN"


def build_reflection_candidate(
    packet: Mapping[str, object],
    request: Mapping[str, object],
    *,
    expected_tested_sha: str | None = None,
    expected_change_head_sha: str | None = None,
) -> ReflectionCandidate:
    """Validate CI provenance, then delegate hypothesis semantics to the core."""

    validate_failure_packet(packet)
    classification_evidence_refs = string_list(
        request,
        "classification_evidence_refs",
        required=True,
    )

    raw_domain = required_text(request, "failure_domain")
    try:
        domain = FailureDomain(raw_domain)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in FailureDomain)
        raise ValueError(f"failure_domain must be one of: {allowed}") from exc

    subject = packet["subject"]
    assert isinstance(subject, dict)
    subject_kind = required_text(subject, "kind")
    tested_sha = required_text(subject, "tested_sha")
    change_head_sha = required_text(subject, "change_head_sha")
    base_sha_value = subject.get("base_sha")
    base_sha = base_sha_value if isinstance(base_sha_value, str) and base_sha_value else None

    if expected_tested_sha and tested_sha != expected_tested_sha:
        raise ValueError(
            f"tested_sha {tested_sha} does not match expected {expected_tested_sha}"
        )
    if expected_change_head_sha and change_head_sha != expected_change_head_sha:
        raise ValueError(
            "change_head_sha "
            f"{change_head_sha} does not match expected {expected_change_head_sha}"
        )

    routing, next_gate = route_failure_domain(domain)
    digest = packet_digest(packet)
    signature = required_text(packet, "signature")
    observation_root = required_text(packet, "observation_root")
    observed_failure = required_text(packet, "normalized_signal")
    gate = required_text(packet, "gate")

    core = build_reflection_core(
        source_kind="CI_FAILURE",
        source_id=signature,
        source_digest=digest,
        source_evidence_refs=classification_evidence_refs,
        observed_symptom=observed_failure,
        request=request,
        identity_context={
            "source_observation_root": observation_root,
            "source_subject_kind": subject_kind,
            "tested_sha": tested_sha,
            "change_head_sha": change_head_sha,
            "base_sha": base_sha,
            "gate": gate,
            "failure_domain": domain.value,
            "classification_evidence_refs": classification_evidence_refs,
            "routing_disposition": routing.value,
            "next_gate": next_gate,
        },
    )

    return ReflectionCandidate(
        schema=REFLECTION_SCHEMA,
        reflection_id=core.reflection_id,
        branch_key=core.branch_key,
        source_packet_digest=digest,
        source_failure_signature=signature,
        source_observation_root=observation_root,
        source_signal_normalization_version=SIGNAL_NORMALIZATION_VERSION,
        source_subject_kind=subject_kind,
        tested_sha=tested_sha,
        change_head_sha=change_head_sha,
        base_sha=base_sha,
        gate=gate,
        observed_failure=core.observed_symptom,
        failure_domain=domain.value,
        classification_evidence_refs=classification_evidence_refs,
        routing_disposition=routing.value,
        next_gate=next_gate,
        expected_behavior=core.expected_behavior,
        mechanism_hypothesis=core.mechanism_hypothesis,
        evidence_for=core.evidence_for,
        evidence_against=core.evidence_against,
        alternative_explanations=core.alternative_explanations,
        predicted_consequence=core.predicted_consequence,
        required_disconfirmation_test=core.required_disconfirmation_test,
        proposed_scope=core.proposed_scope,
        authority_effect=core.authority_effect,
        promotion_state=core.promotion_state,
    )


def candidate_json(candidate: ReflectionCandidate) -> str:
    return json.dumps(asdict(candidate), indent=2, sort_keys=True) + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--expected-tested-sha")
    parser.add_argument("--expected-change-head-sha")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(packet, dict) or not isinstance(request, dict):
            raise ValueError("packet and request JSON roots must be objects")
        candidate = build_reflection_candidate(
            packet,
            request,
            expected_tested_sha=args.expected_tested_sha,
            expected_change_head_sha=args.expected_change_head_sha,
        )
        output = candidate_json(candidate)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"diagnostic reflection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
