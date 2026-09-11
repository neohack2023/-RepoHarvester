# RELATIONSHIPS_01

Status: PLANNING

## Why this is next

Checkpoint 2 already proves deterministic TypeScript code-unit harvesting. The next highest-value extension is to connect those exact units with deterministic structural evidence before widening language coverage or adding semantic machinery.

This plan uses the research-phase conclusion that RepoHarvester should deepen its existing evidence spine rather than introduce new infrastructure.

## Goal

Add reproducible relationships for already-supported TypeScript harvest records while preserving exact provenance, RAW lifecycle state, SQLite reproducibility, and extraction receipts.

The first slice is deliberately narrow:

1. parent/child containment evidence
2. import evidence

## Non-goals

Do not include:

- semantic similarity
- embeddings or vector storage
- graph databases
- call graph inference
- architectural role classification
- LLM-generated relationships
- cross-repository relationship inference
- license qualification
- automatic promotion to VERIFIED or REUSABLE
- second-language extraction

## Current evidence base

Checkpoint 2 provides:

- exact repository/revision provenance
- top-level TypeScript functions, classes, interfaces, type aliases, enums, and variable declarators
- deterministic unit identities
- exact byte/row/column source spans
- SQLite schema v2 with exact symbol/unit queries
- receipt v2 manifest binding
- pinned `anthonylee991/pcm` acceptance evidence

Relationships must extend those records, not create a parallel source of truth.

## Proposed relationship model

Do not freeze beyond demonstrated needs. Minimum candidate fields:

- `source_record_identity`
- `target_record_identity` when resolved to a harvested record
- `relationship_kind`
- `source_repository`
- `source_revision`
- `source_path`
- exact evidence range when syntax-backed
- `literal_target` for unresolved/import syntax
- `resolution_state` such as `EXACT`, `UNRESOLVED`, or `EXTERNAL`
- `extractor_name`
- `extractor_version`
- evidence/manifest hash linkage where useful

Suggested first relationship kinds:

- `contains`
- `imports`

Reverse traversal (`contained_by`, `imported_by`) should preferably be query behavior over directed evidence rather than duplicated stored rows unless tests demonstrate a need for materialized reverse edges.

## Gate A — containment design

Checkpoint 2 intentionally limited extraction to top-level units, so parent/child work must first define what counts as an admitted child unit.

Research/implementation decision:

- prefer parser-backed containment only
- add the narrowest child declaration set justified by PCM fixtures
- likely first candidates are class/interface members or nested named declarations, but do not widen automatically
- every child must retain exact source spans and a deterministic parent identity

Required fixtures:

- class with multiple methods
- duplicate method names in different classes
- nested named function where supported
- interface members if admitted
- malformed/incomplete class body

Exit: deterministic parent identity and child identity rules are documented and tested.

## Gate B — import evidence

Extract explicit TypeScript import syntax deterministically.

Initial syntax coverage should be bounded to forms demonstrated by fixtures/PCM, including as needed:

- default imports
- named imports
- namespace imports
- side-effect imports
- relative imports
- package/external imports
- type-only imports when supported by the selected grammar version

Preserve the literal module specifier exactly as source evidence.

Resolution rules:

- repository-local resolution may be added only when deterministic under an explicit rule set
- unresolved specifiers remain `UNRESOLVED`
- package imports remain `EXTERNAL` unless a later dependency-evidence slice resolves them
- do not inspect network/package registries in this slice

Exit: deterministic import evidence and resolution-state tests pass.

## Gate C — storage migration

Extend SQLite from schema v2 only as required.

Preferred design is a separate relationship table referencing stable harvest-record identities/IDs rather than embedding relationship arrays into records.

Requirements:

- explicit v2 -> v3 migration if schema changes
- preserve all v2 records/tags
- idempotent migration/init
- deterministic uniqueness semantics for edges
- exact query by repository/revision, relationship kind, source identity, target identity, and literal target where applicable
- cycles supported
- unresolved/external imports representable without fake target records

Exit: migration, round-trip, duplicate-edge, cycle, and exact-query tests pass.

## Gate D — receipt/evidence binding

Relationship evidence must be reproducible.

Either extend receipt v2 compatibly or introduce a versioned receipt update that binds:

- relationship count
- relationship kinds
- canonical relationship manifest hash
- extractor/ruleset versions
- warnings/unresolved counts
- database schema version

The manifest must drift when direction, kind, source/target identity, literal import target, or evidence range changes.

Exit: deterministic ordering and mutation/drift tests pass.

## Gate E — pinned PCM acceptance

Preferred target remains:

`anthonylee991/pcm@5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`

Acceptance path:

`exact checkout -> file records -> TypeScript units -> relationships -> SQLite -> exact relationship queries -> receipt/reproduction -> clean source worktree`

Evidence should report:

- record count
- child-unit count if extraction expands
- relationship count by kind
- exact/unresolved/external import counts
- schema version
- manifest hash
- parser/extractor/ruleset versions
- warnings
- source worktree cleanliness

Checkpoint only if repeated runs at the same revision produce the same admitted identities and relationship manifest.

## Tests required before checkpoint

At minimum:

- deterministic relationship ordering
- duplicate names in different parents
- exact parent identity
- multiple imports from same module
- side-effect import
- type-only import if admitted
- relative/local import resolution
- unresolved relative import
- external package import
- cyclic imports
- schema v2 -> v3 preservation
- relationship upsert/idempotency
- exact relationship queries
- receipt relationship drift detection
- pinned PCM acceptance
- source worktree remains clean

## Checkpoint target

`CHECKPOINT 3 — deterministic TypeScript relationships`

Checkpoint 3 is reached when supported TypeScript records can be connected by reproducible parser-backed containment and import evidence at an exact repository revision, stored and exactly queried locally, reproduced from receipts, and validated on a pinned external repository without changing qualification state or mutating source.

## Follow-up ordering after Checkpoint 3

Research from the gap audit suggests this order unless a real target changes priority:

1. `RECEIPT_SCHEMA_VALIDATION_01` — fail-closed schema/version validation.
2. `LICENSE_EVIDENCE_01` — repository/file declarations normalized to SPDX expressions with evidence scope.
3. `DEPENDENCY_EVIDENCE_01` — resolve package/import dependencies beyond literal syntax.
4. `QUALIFICATION_GATE_01` — explicit evidence-backed lifecycle transitions.
5. `CROSS_REPO_COMPARISON_01` — deterministic comparison and relationship of units across exact revisions.
6. Add a second extraction language only when a concrete target requires it.

## Stop conditions

Stop and record a blocker rather than broadening scope if:

- containment requires semantic guessing rather than parser evidence
- import resolution becomes environment/package-manager dependent without an explicit deterministic contract
- schema migration risks existing checkpoint evidence
- relationship identity cannot remain stable under repeated extraction of identical source
- adding a second language appears necessary only to make the slice feel more complete

The correct response is a narrower repair or explicit follow-up slice, not more infrastructure.
