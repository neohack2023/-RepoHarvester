#!/usr/bin/env python3
"""Shared authority-neutral reflection semantics for DevOS evidence adapters.

Source adapters own provenance validation. This module owns the hypothesis
contract shared by CI-failure and evidence-delta reflections.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence

REFLECTION_CORE_SCHEMA = "repoharvester-reflection-core/v1"


@dataclass(frozen=True)
class ReflectionCore:
    schema: str
    reflection_id: str
    source_kind: str
    source_id: str
    source_digest: str
    source_evidence_refs: tuple[str, ...]
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


def required_text(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def string_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    required: bool,
) -> tuple[str, ...]:
    value = mapping.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    items = tuple(sorted({item.strip() for item in value if item.strip()}))
    if required and not items:
        raise ValueError(f"{key} must contain at least one non-empty value")
    return items


def canonical_digest(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_reflection_core(
    *,
    source_kind: str,
    source_id: str,
    source_digest: str,
    source_evidence_refs: Sequence[str],
    observed_symptom: str,
    request: Mapping[str, object],
    identity_context: Mapping[str, object] | None = None,
) -> ReflectionCore:
    """Build deterministic hypothesis semantics independent of source type.

    ``identity_context`` participates in reflection identity but is deliberately
    adapter-owned. This lets a CI adapter bind exact tested/change-head SHAs
    while a delta adapter binds lineage/triangulation state without forcing one
    source model onto the other.
    """

    if not source_kind.strip():
        raise ValueError("source_kind must be non-empty")
    if not source_id.strip():
        raise ValueError("source_id must be non-empty")
    if not source_digest.startswith("sha256:"):
        raise ValueError("source_digest must be a sha256 digest")
    if not observed_symptom.strip():
        raise ValueError("observed_symptom must be non-empty")

    refs = tuple(sorted({ref.strip() for ref in source_evidence_refs if ref.strip()}))
    if not refs:
        raise ValueError("source_evidence_refs must contain at least one reference")

    branch_key = required_text(request, "branch_key")
    expected_behavior = required_text(request, "expected_behavior")
    mechanism_hypothesis = required_text(request, "mechanism_hypothesis")
    alternatives = string_list(request, "alternative_explanations", required=True)
    predicted_consequence = required_text(request, "predicted_consequence")
    disconfirmation_test = required_text(request, "required_disconfirmation_test")
    proposed_scope = required_text(request, "proposed_scope")
    evidence_for = string_list(request, "evidence_for", required=False)
    evidence_against = string_list(request, "evidence_against", required=False)

    payload = {
        "schema": REFLECTION_CORE_SCHEMA,
        "source_kind": source_kind.strip(),
        "source_id": source_id.strip(),
        "source_digest": source_digest,
        "source_evidence_refs": refs,
        "branch_key": branch_key,
        "observed_symptom": observed_symptom.strip(),
        "expected_behavior": expected_behavior,
        "mechanism_hypothesis": mechanism_hypothesis,
        "evidence_for": evidence_for,
        "evidence_against": evidence_against,
        "alternative_explanations": alternatives,
        "predicted_consequence": predicted_consequence,
        "required_disconfirmation_test": disconfirmation_test,
        "proposed_scope": proposed_scope,
        "authority_effect": "NONE",
        "promotion_state": "CANDIDATE_ONLY",
    }
    identity_payload = {
        "core": payload,
        "adapter_identity_context": dict(identity_context or {}),
    }
    reflection_id = "reflection-" + canonical_digest(identity_payload).split(":", 1)[1][:16]
    return ReflectionCore(reflection_id=reflection_id, **payload)


def core_to_json(core: ReflectionCore) -> str:
    return json.dumps(asdict(core), indent=2, sort_keys=True) + "\n"
