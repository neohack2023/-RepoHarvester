# RELATIONSHIPS_01

Status: CHECKPOINTED — see `CHECKPOINT.md` Checkpoint 3

## Outcome

Checkpoint 3 proves deterministic TypeScript relationship harvesting on the pinned external PCM repository without changing qualification state or mutating harvested source.

Implemented:

- first-class directed relationship records
- file -> top-level symbol `contains` edges
- parser-backed file -> import-target `imports` edges
- explicit `EXACT`, `UNRESOLVED`, and `EXTERNAL` import resolution states
- deterministic repository-local relative TypeScript resolution only
- SQLite schema v3 relationship persistence and exact queries
- deterministic v2 -> v3 migration
- receipt v3 relationship-manifest binding
- pinned PCM acceptance with 131 records and 123 relationships
- clean source-worktree verification

Evidence binding:

`6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`

The accepted PCM relationship mix was 87 `contains` and 36 `imports`, with 87 `EXACT`, 20 `UNRESOLVED`, and 16 `EXTERNAL` resolution states.

## Deliberate limits

Do not reinterpret this checkpoint as support for:

- nested/member code-unit extraction
- semantic similarity or semantic dependency resolution
- package-registry or network-backed import resolution
- tsconfig path-alias resolution
- graph databases
- call graph inference
- architectural classification
- cross-repository inferred links
- automatic qualification or promotion

Containment currently connects each harvested TypeScript file record to its already-supported top-level symbol records. A later slice may admit nested/member units only when a concrete target justifies the additional identity and provenance rules.

## Validation note

Pinned External Acceptance, CodeQL, conventional-commit validation, and the applicable container build passed for the accepted implementation. Broad inherited CI still contains live third-party-network query-parser tests and therefore is not used as evidence for relationship correctness when those remote hosts fail. Dependency Review also remains unavailable because the repository does not expose the required dependency-graph/security-analysis capability.

## Next frontier

Continue at `RECEIPT_SCHEMA_VALIDATION_01`.

The next bounded slice should make extraction receipts fail closed against explicit supported schemas/versions before RepoHarvester widens license or dependency evidence.

Do not re-implement `RELATIONSHIPS_01`; maintain or extend it only when a demonstrated downstream requirement justifies the change.
