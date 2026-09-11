# RepoHarvester checkpoints

## Checkpoint 1 — first external repository acceptance

- Date: 2026-09-11
- Repository: neohack2023/-RepoHarvester
- Verified main/base before acceptance: ad4525d62064610f76b3ba2cfb6408f32284f052.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: the first bounded end-to-end external repository path is proven: exact Git provenance -> structured RAW
  file records -> deterministic baseline tags -> local SQLite persistence -> exact provenance query/reload ->
  deterministic extraction receipt -> reproduction verification, without modifying the harvested repository.
- Acceptance evidence: PCM traversal produced 44 file records. SQLite stored and exactly reloaded 44/44 records.
  All records remained `RAW`; receipt verification passed; the external worktree remained clean.
- Evidence binding: receipt manifest SHA-256
  `644fb514b3dafc6c19f0260d5556ece2c7bb8dbb14aececad12598fa0f438cf7`.
- Qualification: CHECKPOINT 1 REACHED. No external code, claim, or pattern was promoted to reusable knowledge.

## Checkpoint 2 — deterministic TypeScript code units

- Date: 2026-09-11
- Verified implementation base: `70c6cce3369a413cbe81948be190c6a4ade0566f`.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: file-level harvesting now deterministically decomposes supported TypeScript files into provenance-backed
  top-level named code units while preserving the file evidence chain.
- Implemented code units: top-level functions, classes, interfaces, type aliases, enums, and variable declarators.
  Nested methods and arbitrary nested AST nodes remain deliberately out of scope.
- Provenance and identity: every code-unit record retains repository, exact revision, file path, parent file SHA-256,
  exact representation SHA-256, deterministic unit identity, symbol name, and zero-based byte/row/column source spans.
- Storage: SQLite schema version 2 distinguishes multiple units in the same file using
  `(repository, revision, path, unit_kind, unit_identity)` and supports exact `symbol_name` and `unit_identity` queries.
  A deterministic v1 -> v2 migration preserves existing file records and tags.
- Receipt: extraction receipt version 2 binds code-unit identity and source spans into the canonical manifest.
- Parser: `tree-sitter==0.21.3` with `tree-sitter-typescript==0.21.2`, pinned to preserve the existing Python 3.8
  support floor while providing deterministic TypeScript syntax trees and source ranges.
- Acceptance evidence: GitHub Actions `External Acceptance` passed against the pinned PCM revision. The run produced
  44 file records plus 87 TypeScript symbol records = 131 total records. SQLite stored/reloaded all 131 exactly;
  exact symbol-name lookup passed; receipt reproduction passed; all records remained `RAW`; source worktree stayed clean.
- PCM symbol mix: 23 functions, 5 classes, 23 interfaces, 12 type aliases, 24 variables.
- Evidence binding: receipt manifest SHA-256
  `47676c59c8ae724b6e4a58456a8559aa62d6dcddf848e95784faecdc1f841d13`.
- Focused tests: symbol extraction, same-file symbol identity/query, and SQLite schema v1 -> v2 migration passed.
  CodeQL and conventional-commit validation passed.
- CI warning: the inherited host-agnostic query-parser tests make live `git ls-remote` calls to third-party hosts.
  The observed broad-CI failure was limited to five such cases: Bitbucket authentication behavior and an Alpine GitLab
  HTTP 418 response. In the same test run, all RepoHarvester symbol/storage/receipt tests passed (197 tests passed total,
  five inherited network-dependent tests failed). This is not evidence of a TypeScript harvesting defect.
- Existing repository warning: Dependency Review remains non-executable because the repository does not currently expose
  the required dependency-graph/security-analysis capability.
- Qualification: CHECKPOINT 2 REACHED for deterministic TypeScript code-unit harvesting. Every PCM code unit remains
  `RAW`; no code or architectural conclusion is promoted to trusted reusable knowledge.
- Known risks: extraction is top-level only; source-position identity will intentionally change when source text moves;
  TSX is not yet supported; overloaded/member declarations are not modeled; license metadata is still not attached to
  each record; external-network upstream tests remain nondeterministic.
- Next gate: choose one evidence-backed extension rather than widening automatically: either model parent/child and
  import relationships for the TypeScript units already harvested, or add a second language when a real target requires it.
  Do not add semantic ranking, vectors, distributed infrastructure, or automatic qualification yet.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before the next implementation slice.
