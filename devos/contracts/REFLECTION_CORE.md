# DevOS Reflection Core Contract

Reflection is a hypothesis layer above evidence, not an evidence source and not authority.

## Architecture

```text
CI failure packet ───────────┐
                            ├─> source adapter -> reflection core -> adapter candidate
Evidence-backed delta packet ┘
```

The reflection core owns only semantics that should remain true regardless of evidence source:

- branch scope;
- observed symptom;
- expected behavior;
- mechanism hypothesis;
- evidence for / against;
- at least one alternative explanation;
- predicted consequence;
- required disconfirmation test;
- proposed scope;
- deterministic candidate identity;
- `authority_effect: NONE`;
- `promotion_state: CANDIDATE_ONLY`.

Source adapters own provenance validation and source-specific routing/context.

## Current adapters

### CI failure adapter

`tools/diagnostic_reflection.py` validates `repoharvester-ci-failure/v1`, complete CI subject identity, signal-normalization version, failure-domain evidence refs, and CI-specific routing. Tested/change-head/base SHA remain CI provenance rather than generic reflection fields. Its observed symptom comes from the normalized execution signal, not free-form reflection prose.

### Evidence-delta adapter

`tools/delta_reflection.py` consumes the existing `DeltaPacket` shape from `tools/evidence_runtime.py`. It preserves:

- `source_delta_id` and digest;
- claim key / current claim identity;
- triangulation state;
- independent, correlated, reproduction, and unknown-lineage counts;
- source evidence refs;
- material flag;
- recommended action.

The adapter:

- accepts both the Python-native tuple representation emitted by the runtime object and the JSON-list representation produced by serialization;
- verifies that `delta_id` still matches the deterministic identity of the supplied delta payload;
- derives `observed_symptom` from the delta packet itself rather than accepting an unsupported narrative symptom from the reflection request.

## Separation laws

- Strong evidence for a symptom does not prove a mechanism.
- Multiple competing reflections may share one source evidence object.
- Candidate identity must change when the mechanism or source provenance changes.
- Source evidence must remain addressable; empty evidence references fail closed.
- Observed symptoms come from source adapters; mechanism hypotheses come from reflection requests.
- Adapter routing is a next-step control, not a causal verdict.
- Persistence does not increase authority.
- One evidence source model must not force irrelevant provenance fields onto another.

## Current boundary

This slice establishes generic core semantics and adapters only. It does **not**:

- persist reflection records into SQLite;
- consolidate episodic reflection into semantic/procedural memory;
- update capability maturity;
- select curriculum;
- generate optimizer mutations;
- grant repository or memory mutation authority.

Issue #25 owns the next evaluation. Run a real or controlled RepoHarvester debugging canary through an adapter -> reflection -> disconfirmation path before persistence is treated as warranted.
