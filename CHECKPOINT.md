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

## Checkpoint 3 — deterministic TypeScript relationships

- Date: 2026-09-11
- Merged main head: `84151df2af72deb0df5bb350d031ff17a35278e7`.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: existing provenance-backed file and TypeScript code-unit records now carry deterministic structural evidence
  through first-class directed relationships without changing lifecycle qualification state.
- Implemented relationship kinds: file -> top-level symbol `contains` edges and parser-backed file -> import-target
  `imports` edges. Import evidence preserves literal module specifiers and explicit `EXACT`, `UNRESOLVED`, and `EXTERNAL`
  resolution states; repository-local resolution is limited to deterministic relative TypeScript targets.
- Storage: SQLite schema version 3 adds first-class relationship persistence and exact relationship queries while
  preserving prior records/tags through the v2 -> v3 migration.
- Receipt: extraction receipt version 3 binds the relationship manifest and relationship counts into reproducible evidence.
- Acceptance evidence: pinned PCM acceptance passed with 131 records and 123 relationships: 87 `contains` and 36 `imports`.
  Resolution-state totals were 87 `EXACT`, 20 `UNRESOLVED`, and 16 `EXTERNAL`. SQLite relationship round-trip and exact
  queries passed, receipt reproduction passed, every harvested record remained `RAW`, and the external source worktree
  remained clean.
- Evidence binding: relationship manifest SHA-256
  `6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`.
- Validation: GitHub Actions `External Acceptance`, CodeQL, conventional-commit validation, and the applicable container
  build passed for the merged implementation head.
- CI warning: broad inherited CI still contains live third-party-network query-parser tests. A macOS/Python 3.13 job
  failed inside the generic test step while the RepoHarvester pinned acceptance path passed. This checkpoint does not
  treat that inherited live-network behavior as relationship evidence and does not claim the full matrix was green.
- Existing repository warning: Dependency Review remains non-executable because the repository does not currently expose
  the required dependency-graph/security-analysis capability.
- Qualification: CHECKPOINT 3 REACHED for deterministic TypeScript relationships. No harvested record or relationship was
  promoted beyond `RAW`, and no semantic relationship inference was introduced.
- Known limits: containment currently links files to already-supported top-level TypeScript units rather than introducing
  nested/member code units; import resolution does not consult package managers, registries, tsconfig path aliases, or the
  network; external and unresolved targets remain explicit evidence states rather than fabricated destinations.
- Next gate: `RECEIPT_SCHEMA_VALIDATION_01` — add fail-closed schema/version validation for extraction receipts before
  widening license/dependency evidence. Keep schema validation deterministic and backward-aware for supported receipt
  versions; do not add semantic ranking, vectors, graph infrastructure, or automatic qualification.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before the next implementation slice.

## Checkpoint 4 — fail-closed extraction receipt validation

- Date: 2026-09-11
- Merged main head: `32c516815d6bd6f86c1f7cf77955ad2e91679bb2`.
- Maturity: serialized extraction receipts are now validated against explicit supported version contracts before an
  `ExtractionReceipt` object is constructed or trusted by downstream code.
- Supported serialized versions: `repoharvester-extraction-v1`, `repoharvester-extraction-v2`, and current
  `repoharvester-extraction-v3`. Historical v1/v2 receipts remain loadable for inspection, while current reproduction
  verification requires the current v3 evidence contract.
- Fail-closed behavior: unknown versions, missing required fields, unsupported extra fields, malformed JSON, wrong JSON
  types, malformed lowercase SHA-256 digests, invalid counts/schema versions, and wrong operation identifiers raise
  `ReceiptValidationError` rather than being silently coerced into receipt evidence.
- Compatibility evidence: the first implementation exposed a real Python 3.8 runtime incompatibility from evaluating
  `list[str]` inside `typing.cast`. The CI matrix caught the defect before merge; the deserialization helpers were repaired
  to preserve the repository's Python 3.8 support floor, and the receipt validation/loading tests then passed on Python 3.8.
- Focused validation: the new receipt-validation suite exercises current round-trip verification, version rejection,
  hash/type/count/operation failures, missing/extra fields, malformed/non-object JSON, and backward v2 inspection behavior.
- Acceptance evidence: pinned PCM `External Acceptance` remained green after the receipt boundary hardened, preserving
  Checkpoint 3's 131 records, 123 deterministic relationships, clean source worktree, and relationship manifest SHA-256
  `6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`.
- Validation: CodeQL and conventional-commit validation passed on the accepted head. On both Python 3.8 and Python 3.13,
  the RepoHarvester receipt tests passed; the only observed broad-CI test failures were the already-documented five inherited
  live-network query-parser cases involving Bitbucket authentication behavior and Alpine GitLab HTTP 418 responses.
- Existing repository warning: Dependency Review remains non-executable because the repository does not currently expose
  the required dependency-graph/security-analysis capability.
- Qualification: CHECKPOINT 4 REACHED. Receipt validation hardens evidence admission only; no harvested records or
  relationships changed lifecycle state, and no external code was promoted to reusable knowledge.
- Known limits: validation is an explicit in-code serialized contract rather than a standalone JSON Schema artifact;
  historical receipts are supported for inspection but are not silently upgraded or accepted as current reproduction proof.
- Next gate: `LICENSE_EVIDENCE_01` — attach deterministic, provenance-backed repository license evidence without inferring
  per-file reuse rights or promoting any record. Prefer exact license-file evidence and normalized identifiers only when
  the source supports them deterministically; preserve unknown/ambiguous cases explicitly.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before the next implementation slice.

## Checkpoint 5 — deterministic repository license evidence

- Date: 2026-09-11
- Merged main head: `d38ecd0859d4576dd00ffb5180791b8589a6fba7`.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: repository-level license documents can now enter the same provenance-backed evidence spine as other harvested
  units without implying that every file inherits the repository license or changing any qualification state.
- Discovery boundary: only conventional root-level license filenames are admitted by `repository-license-v1`; nested,
  vendored, README, or arbitrary license-like files are not treated as repository-license evidence in this slice.
- Evidence shape: each admitted license document becomes a distinct RAW `evidence:repository-license` harvest record that
  preserves exact repository, revision, path, source SHA-256, representation SHA-256, and exact decoded license text.
- Normalization: canonical MIT text is deterministically tagged `license:spdx:MIT`. Unsupported, custom, incomplete, or
  ambiguous text is retained as exact evidence and tagged `license:spdx:UNKNOWN` rather than being guessed.
- Storage: the existing SQLite v3 record spine is reused deliberately; no new table or schema migration was required.
  Exact provenance/unit-kind/tag queries and the existing extraction-receipt manifest bind the license evidence.
- Acceptance evidence: pinned PCM acceptance produced 44 file records + 87 TypeScript symbol records + 1 repository-license
  evidence record = 132 total records. SQLite stored/reloaded all 132 exactly. The license record came from root `LICENSE`,
  retained exact text, carried `license:spdx:MIT`, remained `RAW`, and the source checkout stayed clean.
- Relationship evidence: the existing 123 relationships were unchanged: 87 `contains` and 36 `imports`, with 87 `EXACT`,
  20 `UNRESOLVED`, and 16 `EXTERNAL` resolution states.
- Evidence binding: receipt manifest SHA-256
  `ffd3bdf8573c7a21a7a23fbcac505117479a86c72741706c6d605bad0606dc4a`.
  Relationship manifest SHA-256 remained
  `6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`.
- Validation: pinned `External Acceptance`, CodeQL, conventional-commit validation, and container build passed. On Python
  3.8 and Python 3.13, all RepoHarvester product tests including license evidence passed; the broad matrix still reported
  only the same five inherited live-network query-parser failures involving Bitbucket authentication and Alpine GitLab 418.
- Existing repository warning: Dependency Review remains non-executable because the repository does not currently expose
  the required dependency-graph/security-analysis capability.
- Qualification: CHECKPOINT 5 REACHED. License evidence remains RAW evidence. No per-file reuse right, legal conclusion,
  compatibility conclusion, or promotion to reusable knowledge is inferred from the repository-level license document.
- Known limits: root conventional filenames only; canonical MIT normalization only; no fuzzy matching, SPDX header scan,
  nested/vendor interpretation, per-file license attribution, package metadata licensing, network lookup, or legal advice.
- Next gate: `DEPENDENCY_EVIDENCE_01` — deterministically capture declared dependency evidence from a concrete manifest
  format justified by the pinned target, preserve exact manifest provenance, avoid package-registry/network resolution,
  and keep all resulting evidence RAW.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before the next implementation slice.
