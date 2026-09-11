# CODE_UNIT_EXTRACTION_01

Status: PLANNING

## Why this is next

Checkpoint 1 proved deterministic external harvesting at file granularity. The current frontier is to move from whole-file records to exact code units that can later support pattern classification, comparison, qualification, and agent retrieval without losing provenance.

This plan intentionally stops before semantic ranking, vector search, automated qualification, or cross-repository promotion.

## Research conclusions carried forward

1. RepoHarvester already has the correct evidence spine: exact repository/revision provenance, hashes, deterministic tags, SQLite, exact queries, receipts, and reproduction verification.
2. The next missing primitive is deterministic symbol/code-unit extraction.
3. Tree-sitter is the preferred general parsing architecture because it provides concrete syntax trees and robust parsing across many languages, including partially invalid source.
4. The current Python `tree-sitter-typescript` package may require a newer Python version than the inherited gitingest Python 3.8 floor. Parser adoption therefore needs a compatibility gate instead of an automatic dependency addition.
5. SCIP is useful as a design reference for exact source ranges, symbol identities, occurrences, and progressive indexer maturity, but implementing SCIP itself would be premature.
6. SQLite should remain the local persistence layer. Extending the schema requires an explicit migration path rather than overwriting schema version 1 behavior.
7. Receipt JSON currently assumes trusted shape. Code-unit work should not expand that trust boundary accidentally; strict receipt/schema validation is a nearby but separable follow-up.
8. License evidence is required before reusable promotion, but it is not part of this slice.

Research references:

- Tree-sitter: https://tree-sitter.github.io/
- Tree-sitter Python bindings: https://github.com/tree-sitter/py-tree-sitter
- Tree-sitter TypeScript grammar: https://github.com/tree-sitter/tree-sitter-typescript
- TypeScript Compiler API: https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
- SCIP: https://github.com/sourcegraph/scip
- Sourcegraph indexer guidance: https://sourcegraph.com/docs/code-navigation/writing-an-indexer
- SQLite `user_version`: https://www.sqlite.org/pragma.html#pragma_user_version

## Goal

Prove one supported language can be deterministically broken into provenance-backed code-unit records that survive storage, exact retrieval, and receipt reproduction at an exact repository revision.

## Non-goals

Do not include:

- semantic/architectural classification
- LLM-generated tags
- similarity ranking or embeddings
- vector databases
- cross-repository comparison
- dependency graphs beyond fields strictly required by the selected extractor
- license qualification
- automatic lifecycle promotion
- automatic code copying
- distributed infrastructure

## Capability-overlap disposition

| Capability | Disposition | Action |
| --- | --- | --- |
| Existing file harvest records | EXACT_MATCH | Extend; do not replace |
| SQLite store/query layer | EXTENSION_CANDIDATE | Add versioned code-unit persistence/query support |
| Extraction receipts | EXTENSION_CANDIDATE | Bind code-unit identities/extractor evidence |
| Tree-sitter | EXTENSION_CANDIDATE | Qualify as parser candidate |
| TypeScript Compiler API | PARTIAL_OVERLAP | Retain as fallback/later semantic option |
| SCIP | PARTIAL_OVERLAP | Use as identity/range design reference only |
| Vector/graph databases | NO_MATCH for current need | Do not add |

## Proposed record shape

Do not freeze this permanently. The first implementation should prove only fields justified by the workflow.

Minimum candidate fields:

- `source_repository`
- `source_revision`
- `path`
- `language`
- `unit_kind`
- `symbol_name` or bounded anonymous identity
- `qualified_name` when deterministically available
- `start_byte`
- `end_byte`
- `start_line`
- `start_column`
- `end_line`
- `end_column`
- `parent_unit_identity` when nested
- `source_sha256` for the parent file evidence
- `representation_sha256` for the extracted unit representation
- `representation`
- `extractor_name`
- `extractor_version`
- `qualification_state = RAW`
- deterministic tags/ruleset where applicable

A stable unit identity should be derived deterministically from provenance plus exact unit identity/range information. Human-readable names are not sufficient because duplicate and nested declarations exist.

## Planning gates

### Gate A — parser qualification

Compare the smallest credible parser paths for one language.

The qualification fixture must include:

- ordinary named functions/classes/methods as applicable
- nested declarations
- duplicate symbol names in distinct scopes
- anonymous constructs if the language exposes them
- comments/docstrings around declarations
- CRLF and LF variants
- a syntax-error or incomplete-source case
- malformed source that must not create fabricated units

Record:

- parser/runtime dependency
- Python/runtime compatibility impact
- deterministic range behavior
- invalid-syntax behavior
- package license/maintenance status
- version string suitable for receipts

Exit: one parser path selected, or an explicit blocker recorded.

### Gate B — code-unit model and extractor

Implement one extractor behind a small deterministic interface.

Requirements:

- no LLM calls
- exact ranges
- stable deterministic ordering
- stable identities across repeated extraction of identical source
- nested units remain distinguishable
- duplicate names remain distinguishable
- malformed input behavior is explicit
- all units start as `RAW`

Exit: focused extraction tests pass.

### Gate C — SQLite schema v2 migration

Extend storage only as required for code units.

Requirements:

- preserve existing schema-v1 file data
- explicit v1 -> v2 migration
- idempotent initialization
- reject or explicitly handle unsupported future schema versions
- deterministic code-unit inserts/upserts
- exact queries by repository, revision, path, language, unit kind, and stable unit identity
- existing file-record retrieval remains lossless

Exit: migration + round-trip + idempotency tests pass.

### Gate D — receipt binding

Extend extraction evidence so reproduction can prove the same code units were produced.

Receipt evidence should include, at minimum:

- repository/revision
- record/unit counts
- deterministic manifest hash
- extractor name/version
- database schema version
- warnings/conflicts
- next gate

The manifest must change when unit identity, source range, representation hash, or relevant provenance evidence changes.

Exit: order-independent reproduction passes and mutation/drift tests fail verification as expected.

### Gate E — real pinned acceptance

Run the new path on a pinned repository revision suited to the selected language. `anthonylee991/pcm@5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8` is the preferred continuation if TypeScript is selected and the parser compatibility gate passes.

Acceptance path:

`exact checkout -> file harvest -> code-unit extraction -> SQLite store -> exact query/reload -> receipt -> reproduction verification -> clean source worktree`

Exit conditions:

- source remains unmodified
- exact revision proven
- deterministic repeated extraction produces identical identities/counts/manifests
- SQLite reload reproduces the harvested units
- receipt verifies
- CI is green for the bounded acceptance job

## Tests required before checkpoint

At minimum:

- repeated extraction determinism
- source-range correctness
- duplicate-name identity distinction
- nesting/parent identity
- malformed/incomplete input behavior
- CRLF/LF evidence behavior explicitly defined and tested
- schema v1 -> v2 migration
- existing file-record regression tests
- code-unit SQLite round trip
- exact query semantics
- receipt order independence
- receipt drift detection
- pinned acceptance repository or accepted deterministic fixture
- source worktree cleanliness

## Checkpoint target

`CHECKPOINT 2 — deterministic code-unit evidence`

A checkpoint is warranted only when one supported language can be ingested at an exact revision, decomposed into deterministic code units with exact source identity, stored/queryable in the local database, reproduced from evidence, and accompanied by an extraction receipt without mutating the source repository.

Checkpoint evidence should capture:

- exact RepoHarvester head
- exact target repository/revision
- selected extractor + version
- language supported
- unit counts/kinds
- schema version/migration evidence
- test/CI evidence
- manifest hash
- warnings and unsupported syntax
- next bounded gate

## Follow-up sequence after Checkpoint 2

These are ordered research/implementation candidates, not part of this slice:

1. `RECEIPT_SCHEMA_VALIDATION_01` — fail-closed JSON/receipt version validation.
2. `LICENSE_EVIDENCE_01` — deterministic repository/file license declarations normalized to SPDX expressions with evidence scope.
3. `DEPENDENCY_EVIDENCE_01` — deterministic imports/package dependencies for the supported language.
4. `QUALIFICATION_GATE_01` — explicit evidence-backed lifecycle transitions; no confidence-score shortcut.
5. `RELATIONSHIPS_01` — contains/defines/imports/supersedes and similar evidence-backed relationships.
6. `CROSS_REPO_COMPARISON_01` — compare code units across exact revisions while preserving disagreements and provenance.
7. RepoHarvester-facing CLI/API retrieval surface for coding agents.

## Stop conditions

Stop and record a blocker instead of broadening the slice if:

- the selected parser requires an unapproved compatibility break
- stable source ranges cannot be reproduced
- schema migration risks existing stored evidence
- extractor output cannot distinguish duplicate/nested units deterministically
- the implementation needs semantic interpretation to establish basic symbol boundaries

The correct response to those failures is a narrower repair or parser re-evaluation, not additional infrastructure.
