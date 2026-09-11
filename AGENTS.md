# RepoHarvester agent contract

RepoHarvester is a controlled fork of `coderamp-labs/gitingest` that extends prompt-friendly repository ingestion into provenance-backed code harvesting and reusable code intelligence.

## Authority and resume rules

- GitHub `main` is the engineering and implementation source of truth.
- Re-check the current repository head and `CHECKPOINT.md` before making implementation claims or starting a new slice.
- Preserve upstream gitingest behavior unless a change is deliberate, bounded, and tested.
- Do not modify harvested source repositories during harvesting or qualification.

## Core separation

Keep these concerns distinct:

1. raw source evidence
2. derived deterministic metadata
3. interpretation/classification
4. qualification/validation
5. promoted reusable knowledge

Candidate discovery is not qualification. External code must never be silently promoted to trusted reusable knowledge.

## Qualification lifecycle

Use explicit states where applicable:

`RAW -> CANDIDATE -> TAGGED -> VERIFIED -> REUSABLE`

Terminal/lineage states may include `REJECTED` and `SUPERSEDED`.

State transitions must eventually be backed by explicit evidence and admission rules. Storage, extraction, receipt validation, relationship discovery, license discovery, and dependency discovery must not infer promotion by themselves.

## Provenance requirements

Every harvested unit must retain enough identity to reproduce its origin. Preserve, as applicable:

- source repository
- exact source revision
- file path
- code-unit/symbol identity
- exact source location
- language
- source and representation hashes
- deterministic tags/ruleset
- license/provenance evidence
- dependency evidence
- qualification state
- validation/evidence references
- extraction receipt linkage

## Implementation style

Prefer:

`small patch -> focused tests -> inspect result -> record evidence -> checkpoint when warranted`

Repair the narrowest demonstrated defect. Do not broaden heuristics speculatively.

Prefer deterministic tooling for parsing, hashing, extraction, indexing, comparison, schema validation, database operations, and reproduction checks. LLM interpretation belongs above those deterministic evidence layers.

## Scope control

Do not introduce distributed databases, large vector infrastructure, autonomous multi-agent orchestration, automatic code copying, automatic promotion, or complex governance layers until demonstrated workflow requirements justify them.

SQLite remains the default local database unless workload evidence proves otherwise.

## Feature routing

Feature-specific agent contracts live under `features/<feature>/AGENTS.md` and override this file only within their bounded feature responsibility.

Current feature cells:

- `features/storage/` — SQLite persistence and exact deterministic retrieval
- `features/code-units/` — deterministic TypeScript code-unit extraction, checkpointed at Checkpoint 2
- `features/relationships/` — deterministic TypeScript containment/import evidence, checkpointed at Checkpoint 3
- extraction receipts — fail-closed serialized version/shape validation, checkpointed at Checkpoint 4
- repository license evidence — deterministic root license evidence and conservative SPDX tagging, checkpointed at Checkpoint 5
- declared dependency evidence — deterministic root `package.json` `dependencies`/`devDependencies` evidence, checkpointed at Checkpoint 6

## Current frontier

Checkpoint 1 proved deterministic external file-level harvesting with provenance, tags, SQLite, exact retrieval, and receipts.

Checkpoint 2 proved deterministic TypeScript code-unit harvesting at exact source locations, SQLite schema v2 migration/query behavior, receipt v2 evidence, and pinned PCM acceptance.

Checkpoint 3 proved deterministic TypeScript `contains` and `imports` relationships, SQLite schema v3 persistence/query behavior, receipt v3 relationship binding, and pinned PCM acceptance. All harvested records and relationships remain evidence only; nothing was promoted beyond `RAW`.

Checkpoint 4 hardened serialized extraction-receipt admission with explicit supported versions and fail-closed validation while preserving the Python 3.8 support floor.

Checkpoint 5 proved deterministic root repository-license evidence on the pinned PCM target. Canonical MIT text is tagged `license:spdx:MIT`; unsupported or ambiguous text remains exact RAW evidence tagged `license:spdx:UNKNOWN`. No per-file license or legal conclusion is inferred.

Checkpoint 6 proved deterministic direct dependency evidence from the pinned target's root `package.json`. Exact package names and version expressions are preserved for `dependencies` and `devDependencies`, runtime/development scope is explicit, malformed admitted declarations fail closed, and no registry, lockfile, transitive, vulnerability, license, or qualification inference is performed.

The next bounded frontier is `QUALIFICATION_GATE_01`: define the smallest explicit evidence-backed lifecycle transition. Qualification must consume the evidence already harvested rather than manufacture facts. Missing, ambiguous, stale, or incompatible evidence must block promotion rather than be guessed.

For `QUALIFICATION_GATE_01`:

- start with one narrowly defined transition justified by the pinned acceptance workflow rather than implementing the whole lifecycle at once
- bind every transition to exact repository/revision/unit identity and explicit evidence references
- keep evidence records immutable as evidence; record qualification disposition separately when practical
- require deterministic admission checks where facts are machine-checkable
- do not treat repository license evidence as automatic per-file reuse permission
- do not treat dependency declarations as compatibility or safety proof
- do not automatically promote anything to `REUSABLE`
- do not introduce a generic policy engine, semantic ranking, vectors, or distributed infrastructure
- preserve explicit rejection/blocking reasons and leave the source repository untouched

Likely follow-up after a proven qualification gate is `CROSS_REPO_COMPARISON_01`. A second language should be added only when a concrete target requires it.

Do not add semantic ranking, vectors, distributed infrastructure, or automatic qualification as part of the current frontier.
