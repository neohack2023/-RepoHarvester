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

## Checkpoint 6 — deterministic declared dependency evidence

- Date: 2026-09-11
- Implementation merge on `main`: `75b8412f2fa608b364c8f3513e7e61a072fbc9fa`.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: direct dependency declarations from the pinned target's root `package.json` now enter the existing
  provenance-backed harvest-record evidence spine without package-manager resolution, registry lookup, or qualification
  promotion.
- Admission boundary: `package-json-dependencies-v1` admits only root `package.json` `dependencies` and
  `devDependencies`. Runtime and development scope is recorded deterministically, exact package names and version
  expressions are preserved verbatim, and malformed admitted sections/non-string declarations fail closed.
- Deliberate exclusion: `trustedDependencies` is not treated as a versioned dependency requirement because it carries
  trust/install semantics rather than a declared version requirement. Peer, optional, lockfile, and transitive dependency
  evidence remain out of scope for this slice.
- Storage and receipt: dependency declarations are distinct RAW `evidence:declared-dependency` harvest records using the
  existing SQLite v3 record path and current receipt manifest. No database schema migration or parallel dependency store
  was introduced.
- Acceptance evidence: pinned PCM acceptance produced 44 file records + 87 TypeScript symbol records + 1 repository-license
  evidence record + 6 declared-dependency records = 138 total records. SQLite stored/reloaded all 138 exactly. The six
  declarations split deterministically into 3 runtime and 3 development dependencies; receipt reproduction passed; all
  records remained `RAW`; the harvested source worktree remained clean.
- Relationship evidence: the existing 123 relationships remained unchanged: 87 `contains` and 36 `imports`, with 87
  `EXACT`, 20 `UNRESOLVED`, and 16 `EXTERNAL` resolution states.
- Evidence binding: record manifest SHA-256
  `263a2d10a79da5fb4ce455744d8a7a761a39304a00668511f653cbe6af2b83d9`.
  Relationship manifest SHA-256 remained
  `6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`.
- Validation: exact-head pinned `External Acceptance`, CodeQL, and conventional-commit validation passed. The container
  build-and-push step completed successfully; artifact-attestation generation was skipped by workflow conditions and
  post-job cleanup was still finishing when this checkpoint text was prepared.
- Compatibility evidence: the exact repaired PR head was exercised on Linux, macOS, and Windows under Python 3.8 and
  Python 3.13. In every lane, all 223 non-live-host tests passed, including dependency, evidence, storage, receipt, license,
  relationship, symbol, and tag suites. The only five failures in each lane were the already-documented inherited
  `tests/query_parser/test_git_host_agnostic.py` live-host cases: Bitbucket authentication behavior in full/noscheme forms,
  Alpine GitLab HTTP 418 in full/noscheme forms, and Bitbucket slug host discovery.
- Portability repair: Windows CI exposed a test-contract defect where raw upstream `FileSystemNode.path_str` preserves
  native backslashes while the test compared it against repository-style `/` paths. The test helper now normalizes only
  the comparison form; raw upstream evidence remains untouched and harvest records continue their existing portable path
  normalization. Both Windows 3.8 and 3.13 then passed the RepoHarvester evidence test.
- Existing repository warning: Dependency Review remains non-executable because the repository does not currently expose
  the required dependency-graph/security-analysis capability. This remains a repository configuration/capability issue,
  not dependency-evidence validation.
- Qualification: CHECKPOINT 6 REACHED. Dependency declarations remain RAW provenance evidence. No semantic compatibility,
  vulnerability status, dependency license, trust judgment, version resolution, or promotion is inferred.
- Known limits: root `package.json` only; direct runtime/development declarations only; no peer/optional/trusted dependency
  modeling; no lockfile or transitive graph; no semver/package-registry resolution; no vulnerability or dependency-license
  inference; no qualification transition.
- Next gate: `QUALIFICATION_GATE_01` — define the smallest explicit, evidence-backed lifecycle transition. Qualification
  must consume provenance/receipt/license/dependency/validation evidence explicitly; missing or ambiguous evidence must
  block promotion rather than be guessed. Do not introduce automatic `REUSABLE` promotion or a generic policy engine.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before beginning qualification work.

## Checkpoint 7 — evidence-backed RAW to CANDIDATE qualification

- Date: 2026-09-11
- Implementation merge on `main`: `81566adfd97d589fe40fb2a03906b8440d911837`.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Maturity: RepoHarvester now proves one explicit lifecycle transition, `RAW -> CANDIDATE`, for an exact code-unit identity
  while preserving extraction evidence and qualification evidence as separate deterministic artifacts.
- Gate contract: `raw-to-candidate-v1` admits symbol/code-unit records only. The subject must be present in the evaluated
  harvest set, remain `RAW`, and be backed by a current reproducible extraction receipt for the same repository/revision,
  exactly one explicit non-`UNKNOWN` repository-license evidence record, declared-dependency evidence, and at least one
  explicit validation reference. Missing or ambiguous evidence produces `BLOCKED` with preserved blocking reasons.
- Decision evidence: qualification emits `repoharvester-qualification-decision-v1` records with exact subject identity,
  source/target lifecycle states, disposition, evidence references, blocking reasons, and a deterministic decision SHA-256.
  A separate `repoharvester-qualification-receipt-v1` binds the exact ordered decision hashes into a reproducible manifest.
- State mutation boundary: a PASS decision must match the exact repository/revision/path/unit identity and current state.
  BLOCKED or identity-mismatched decisions cannot alter lifecycle state. Applying a PASS changes only
  `qualification_state`; source/representation hashes, representation, tags, and provenance remain unchanged.
- Pinned acceptance subject: exactly `src/core/associative.ts::computeAssociationWeight`, unit identity
  `typescript:function:computeAssociationWeight:113:373`, was admitted from `RAW` to `CANDIDATE`. All other harvested
  records remained `RAW`.
- Acceptance evidence: the pinned PCM run still contains 138 total records and 123 relationships. SQLite persisted and
  exactly reloaded `1 CANDIDATE / 137 RAW`; the source worktree remained clean; license, dependency, relationship, and
  receipt gates remained passing.
- Evidence binding: prequalification record manifest SHA-256 remained exactly the Checkpoint 6 value
  `263a2d10a79da5fb4ce455744d8a7a761a39304a00668511f653cbe6af2b83d9`. Postqualification record manifest SHA-256 is
  `9e2568ff89b8e96a4a9674b54167e04c96edd7d16521c78bc75fd61daed262ce`.
- Qualification binding: decision SHA-256
  `64595c5f45ebe74fe36f1d9c9ef3dd4672131e46218e89830c386a07e1650128`; decision-manifest SHA-256
  `56c20277aada63b9fa7ffadca49eb74ceed8c668bbca8afda365c7b989a7812c`.
- Relationship evidence remained unchanged: relationship manifest SHA-256
  `6b98e2dcd04ec09a117e7a22ba16b0b0cebd0feb672173a0b3de0faff0cc1ce7`, with 87 `contains` and 36 `imports` edges.
- Durable acceptance artifact: GitHub Actions artifact `pcm-checkpoint-1-evidence`, artifact ID `10283689936`, ZIP digest
  SHA-256 `3d01c9d636909f1c3d03daf108c8d4823e5e2f57266b2aaa2439398b81b372a9`.
- Compatibility evidence: Linux, macOS, and Windows under Python 3.8 and 3.13 each completed with 229 passing tests and only
  the same five inherited live-host failures in `tests/query_parser/test_git_host_agnostic.py`. All six new qualification
  tests passed in every lane. Broad CI is therefore not called green; the product slice is green relative to the documented
  inherited network baseline.
- Validation: pinned `External Acceptance`, both CodeQL lanes, conventional-commit validation, and container build/push
  passed on the accepted head. Dependency Review remains non-executable because dependency graph / Advanced Security is not
  enabled for the repository; this remains a repository capability/configuration issue rather than qualification evidence.
- Test repair: the first synthetic non-reproducible-receipt fixture changed representation text without updating its
  representation SHA-256, so the receipt correctly continued matching the stored hashed identity. The fixture was repaired
  to bind the mutation to a recomputed representation hash; the production qualification contract did not need widening.
- Qualification meaning: `CANDIDATE` means the unit has passed this bounded evidence-completeness admission gate only. It
  does not assert code quality, security, dependency safety, legal compatibility, intended-use compatibility, or reusability.
  No `TAGGED`, `VERIFIED`, or `REUSABLE` promotion is implied.
- Research alignment: the gate deliberately binds exact source revision and evidence digests while keeping candidate
  selection separate from later suitability, dependency, license, security, and validation judgments.
- Qualification: CHECKPOINT 7 REACHED for deterministic `RAW -> CANDIDATE` admission of one pinned external code unit.
- Next gate: `TAGGING_GATE_01` — define the smallest evidence-backed `CANDIDATE -> TAGGED` transition for one accepted code
  unit. Require explicit functional/architectural classification evidence with provenance; preserve disagreements and
  unknowns; do not jump to `VERIFIED` or `REUSABLE`, and do not introduce a generic scoring or policy engine.
- Resume: re-check GitHub `main`, exact head, and this checkpoint evidence before beginning tagging work.


## Checkpoint 8 — repository-local DevOS installation and first self-improvement

- Date: 2026-09-13
- Installation merge on `main`: `b64653de48e9581f806810f1d2e45ae0af2e1ea6` (PR #22).
- Source reference: `neohack2023/project-orath` at exact revision `340e69d2156229188208cb4c5c181da7525175e9`.
- Maturity: RepoHarvester now has an executable repository-local DevOS layer rather than agent instructions alone. It includes branch routing, a unified SQLite knowledge runtime, task and opportunity ledgers, bounded research preflight, reflection/learning tools, STONE/MASON contracts, governance validation, CI, and installation receipts.
- Repo adaptation: six knowledge branches route project core, code units, relationships, storage, qualification lifecycle, and tooling/agent-harness work. GitHub remains live execution authority. RepoHarvester-specific Notion coordinates remain explicitly `UNRESOLVED`; authority-sensitive upstream promotion must stop for bounded synchronization rather than inventing pointers.
- Self-improvement evidence: the installation episode exposed Windows line-ending sensitivity in governance hashes, direct-execution import failures in reflection adapters, and source-project vocabulary leak risk. PR #22 canonicalized governance text hashes to LF, repaired documented direct reflection entrypoints, and added configured leakage validation. Receipt: `devos/receipts/DEVOS-SELF-IMPROVEMENT-20260913-001.json`.
- Validation: `DevOS checks`, `External Acceptance`, `Corpus Harvest Smoke`, CodeQL, container build, and conventional-commit validation passed on PR head `f8bad5dde8f126ea78c22ee99619b4ca01f99e06`. Local DevOS validation passed with six branches; knowledge DB build/check passed; all six focused DevOS tests passed; reflection entrypoint smoke tests and Python compilation passed.
- Existing CI baseline: broad CI still reports five inherited live-host failures involving Bitbucket authentication/GitLab HTTP 418 plus the existing shared-corpus record-order assertion. Dependency Review remains non-executable because the repository lacks the required dependency-graph/security-analysis capability. These did not originate in the DevOS installation.
- Authority effect: the self-improvement receipt is `VERIFIED_LOCAL_DISCOVERY`. It does not self-promote global DevOS authority or rewrite upstream memory.
- Qualification: CHECKPOINT 8 REACHED for repository-local DevOS installation and one evidence-backed self-improvement cycle.
- Product frontier: `TAGGING_GATE_01` remains the next RepoHarvester lifecycle slice. The corpus ordering defect should be repaired independently as the narrowest demonstrated product defect.
- Resume: re-check GitHub `main`, this checkpoint, `devos/governance-lock.json`, and the smallest relevant row in `devos/branches.jsonl` before new work.
