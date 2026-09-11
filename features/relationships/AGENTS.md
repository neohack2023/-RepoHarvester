# Relationships feature agent contract

This feature owns deterministic relationships between provenance-backed harvest records. It does not own semantic interpretation or qualification.

## Current slice

`RELATIONSHIPS_01` is limited to already-supported TypeScript code units and repository-local evidence.

First relationship kinds:

- `contains` / `contained_by` for deterministic parent-child structure
- `imports` / `imported_by` for file/module import evidence

Do not add similarity, semantic dependency ranking, architectural labels, or cross-repository inferred links in this slice.

## Required behavior

- Re-check GitHub `main`, root `AGENTS.md`, and `CHECKPOINT.md` before starting work.
- Relationships must bind exact record identities and source provenance.
- Relationship creation must be deterministic and reproducible from source evidence.
- Preserve directionality explicitly. Do not infer reverse semantics from naming alone.
- Record relationship kind separately from evidence used to establish it.
- Parent/child relationships must come from parser/source structure, not naming heuristics.
- Import relationships must come from explicit import syntax and preserve the literal import target before any resolution attempt.
- Unresolved imports remain unresolved evidence; do not fabricate repository-local destinations.
- Cycles are valid evidence and must not be treated as errors by default.
- Storage must preserve existing records and schema-v2 evidence during any migration.
- Relationship extraction must not change qualification state.

## Scope boundary

This feature does not own:

- semantic similarity
- embeddings/vector search
- call graphs
- inferred runtime behavior
- architecture classification
- license decisions
- reusable-code admission
- cross-repository promotion

## Preferred loop

`small patch -> focused tests -> inspect result -> pinned acceptance -> checkpoint when warranted`

## Checkpoint rule

Checkpoint only when relationships survive deterministic re-extraction, SQLite round-trip/query, receipt/evidence reproduction, and pinned acceptance without mutating the harvested repository.
