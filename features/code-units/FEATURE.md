# CODE_UNIT_EXTRACTION_01

Status: CHECKPOINTED — see `CHECKPOINT.md` Checkpoint 2

## Outcome

The planned deterministic code-unit slice has already landed and passed its bounded acceptance gate.

Implemented:

- TypeScript top-level named code-unit extraction
- functions, classes, interfaces, type aliases, enums, and variable declarators
- exact repository/revision/path provenance
- deterministic unit identity
- exact zero-based byte/row/column source spans
- parent file SHA-256 and unit representation SHA-256
- SQLite schema v2 with v1 -> v2 migration
- exact `symbol_name` and `unit_identity` queries
- extraction receipt v2 binding unit identity and spans
- pinned PCM acceptance at `anthonylee991/pcm@5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`
- 44 file records + 87 TypeScript symbol records = 131 records reproduced exactly
- source worktree remained clean
- all harvested units remained `RAW`

Parser selection:

- `tree-sitter==0.21.3`
- `tree-sitter-typescript==0.21.2`

Those versions were selected specifically to preserve the inherited Python 3.8 compatibility floor while providing deterministic TypeScript syntax trees/source ranges.

## Deliberate limits retained

- top-level extraction only
- TSX not yet supported
- nested/member declarations not yet modeled
- no semantic ranking
- no vectors
- no automatic qualification
- no license evidence attached to each record yet

## Research conclusions that remain useful

- Tree-sitter remains the preferred deterministic parsing architecture for the current supported language.
- SCIP remains a design reference for symbol/range/indexer maturity, not a subsystem requirement.
- SQLite remains the local evidence store until workload evidence proves otherwise.
- receipt shape validation, license evidence, dependency evidence, qualification gates, and cross-repository comparison remain separate follow-up slices.

Research references:

- https://tree-sitter.github.io/
- https://github.com/tree-sitter/py-tree-sitter
- https://github.com/tree-sitter/tree-sitter-typescript
- https://github.com/sourcegraph/scip
- https://sourcegraph.com/docs/code-navigation/writing-an-indexer
- https://www.sqlite.org/pragma.html#pragma_user_version

## Current handoff

Do not re-implement this slice.

Continue from `features/relationships/` for the next bounded frontier: deterministic parent/child and import relationships over the already-harvested TypeScript evidence.
