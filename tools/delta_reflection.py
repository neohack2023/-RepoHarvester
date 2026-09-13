#!/usr/bin/env python3
"""Build authority-neutral reflections from evidence-runtime delta packets.

This adapter preserves delta/triangulation provenance while delegating shared
hypothesis semantics to ``reflection_core``. It does not persist reflections.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence

from tools.reflection_core import (
    build_reflection_core,
    canonical_digest,
    required_text,
)

DELTA_REFLECTION_SCHEMA = "repoharvester-delta-reflection-candidate/v1"
DELTA_IDENTITY_FIELDS = (
    "claim_key",
    "current_claim_id",
    "current_value",
    "observed_values",
    "cross_reference_states",
    "triangulation_state",
    "independent_root_count",
    "correlated_root_count",
    "reproduction_count",
    "unknown_lineage_count",
    "evidence_refs",
    "material",
    "recommended_action",
    "authority_effect",
)


@dataclass(frozen=True)
class DeltaReflectionCandidate:
    schema: str
    reflection_id: str
    source_delta_id: str
    source_delta_digest: str
    claim_key: str
    current_claim_id: str | None
    triangulation_state: str
    independent_root_count: int
    correlated_root_count: int
    reproduction_count: int
    unknown_lineage_count: int
    source_evidence_refs: tuple[str, ...]
    source_material: bool
    source_recommended_action: str
    branch_key: str
    observed_symptom: str
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


def _required_int(mapping: Mapping[str, object], key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def _string_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    required: bool,
) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) for item in value
    ):
        raise ValueError(f"{key} must be a list or tuple of strings")
    items = tuple(sorted({item.strip() for item in value if item.strip()}))
    if required and not items:
        raise ValueError(f"{key} must preserve at least one non-empty reference")
    return items


def expected_delta_id(packet: Mapping[str, object]) -> str:
    payload = {key: packet.get(key) for key in DELTA_IDENTITY_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "delta-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def validate_delta_packet(packet: Mapping[str, object]) -> None:
    if packet.get("authority_effect") != "NONE":
        raise ValueError("source delta must have authority_effect NONE")
    for key in ("delta_id", "claim_key", "triangulation_state", "recommended_action"):
        required_text(packet, key)
    _string_sequence(packet, "observed_values", required=False)
    _string_sequence(packet, "cross_reference_states", required=True)
    _string_sequence(packet, "evidence_refs", required=True)
    if not isinstance(packet.get("material"), bool):
        raise ValueError("source delta material must be boolean")
    for key in (
        "independent_root_count",
        "correlated_root_count",
        "reproduction_count",
        "unknown_lineage_count",
    ):
        _required_int(packet, key)

    supplied_id = required_text(packet, "delta_id")
    if supplied_id != expected_delta_id(packet):
        raise ValueError("source delta_id does not match deterministic delta payload identity")


def delta_digest(packet: Mapping[str, object]) -> str:
    return canonical_digest(packet)


def delta_observed_symptom(packet: Mapping[str, object]) -> str:
    """Render an observation-only symptom directly from the delta packet."""

    claim_key = required_text(packet, "claim_key")
    current = packet.get("current_value")
    current_text = current.strip() if isinstance(current, str) and current.strip() else "<none>"
    observed = _string_sequence(packet, "observed_values", required=False)
    states = _string_sequence(packet, "cross_reference_states", required=True)
    triangulation = required_text(packet, "triangulation_state")
    action = required_text(packet, "recommended_action")
    observed_text = ", ".join(observed) if observed else "<none>"
    return (
        f"claim={claim_key}; current={current_text}; observed={observed_text}; "
        f"cross_reference={','.join(states)}; triangulation={triangulation}; "
        f"recommended_action={action}"
    )


def build_delta_reflection_candidate(
    packet: Mapping[str, object],
    request: Mapping[str, object],
    *,
    expected_delta_id_value: str | None = None,
) -> DeltaReflectionCandidate:
    """Adapt one evidence-backed delta into the shared reflection core."""

    validate_delta_packet(packet)
    delta_id = required_text(packet, "delta_id")
    if expected_delta_id_value and delta_id != expected_delta_id_value:
        raise ValueError(
            f"delta_id {delta_id} does not match expected {expected_delta_id_value}"
        )

    observed_symptom = delta_observed_symptom(packet)
    evidence_refs = _string_sequence(packet, "evidence_refs", required=True)
    digest = delta_digest(packet)
    claim_key = required_text(packet, "claim_key")
    triangulation_state = required_text(packet, "triangulation_state")
    recommended_action = required_text(packet, "recommended_action")
    material = packet["material"]
    assert isinstance(material, bool)

    current_claim_value = packet.get("current_claim_id")
    current_claim_id = (
        current_claim_value
        if isinstance(current_claim_value, str) and current_claim_value.strip()
        else None
    )
    independent_root_count = _required_int(packet, "independent_root_count")
    correlated_root_count = _required_int(packet, "correlated_root_count")
    reproduction_count = _required_int(packet, "reproduction_count")
    unknown_lineage_count = _required_int(packet, "unknown_lineage_count")

    core = build_reflection_core(
        source_kind="EVIDENCE_DELTA",
        source_id=delta_id,
        source_digest=digest,
        source_evidence_refs=evidence_refs,
        observed_symptom=observed_symptom,
        request=request,
        identity_context={
            "claim_key": claim_key,
            "current_claim_id": current_claim_id,
            "triangulation_state": triangulation_state,
            "independent_root_count": independent_root_count,
            "correlated_root_count": correlated_root_count,
            "reproduction_count": reproduction_count,
            "unknown_lineage_count": unknown_lineage_count,
            "material": material,
            "recommended_action": recommended_action,
            "observed_values": packet.get("observed_values", []),
            "cross_reference_states": packet.get("cross_reference_states", []),
        },
    )

    return DeltaReflectionCandidate(
        schema=DELTA_REFLECTION_SCHEMA,
        reflection_id=core.reflection_id,
        source_delta_id=delta_id,
        source_delta_digest=digest,
        claim_key=claim_key,
        current_claim_id=current_claim_id,
        triangulation_state=triangulation_state,
        independent_root_count=independent_root_count,
        correlated_root_count=correlated_root_count,
        reproduction_count=reproduction_count,
        unknown_lineage_count=unknown_lineage_count,
        source_evidence_refs=evidence_refs,
        source_material=material,
        source_recommended_action=recommended_action,
        branch_key=core.branch_key,
        observed_symptom=core.observed_symptom,
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


def candidate_json(candidate: DeltaReflectionCandidate) -> str:
    return json.dumps(asdict(candidate), indent=2, sort_keys=True) + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--expected-delta-id")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        packet = json.loads(args.delta.read_text(encoding="utf-8"))
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(packet, dict) or not isinstance(request, dict):
            raise ValueError("delta and request JSON roots must be objects")
        candidate = build_delta_reflection_candidate(
            packet,
            request,
            expected_delta_id_value=args.expected_delta_id,
        )
        output = candidate_json(candidate)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"delta reflection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
