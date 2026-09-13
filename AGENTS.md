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

State transitions must eventually be backed by explicit evidence and admission rules. Storage, extraction, receipt validation, relationship discovery, license discovery, dependency discovery, and tagging must not infer later promotion by themselves.

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
- qualification decision/receipt linkage

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
- qualification decisions — deterministic evidence-backed `RAW -> CANDIDATE` admission with separate decision/receipt artifacts, checkpointed at Checkpoint 7

## Current frontier

Checkpoint 1 proved deterministic external file-level harvesting with provenance, tags, SQLite, exact retrieval, and receipts.

Checkpoint 2 proved deterministic TypeScript code-unit harvesting at exact source locations, SQLite schema v2 migration/query behavior, receipt v2 evidence, and pinned PCM acceptance.

Checkpoint 3 proved deterministic TypeScript `contains` and `imports` relationships, SQLite schema v3 persistence/query behavior, receipt v3 relationship binding, and pinned PCM acceptance.

Checkpoint 4 hardened serialized extraction-receipt admission with explicit supported versions and fail-closed validation while preserving the Python 3.8 support floor.

Checkpoint 5 proved deterministic root repository-license evidence on the pinned PCM target. Canonical MIT text is tagged `license:spdx:MIT`; unsupported or ambiguous text remains exact RAW evidence tagged `license:spdx:UNKNOWN`. No per-file license or legal conclusion is inferred.

Checkpoint 6 proved deterministic direct dependency evidence from the pinned target's root `package.json`. Exact package names and version expressions are preserved for `dependencies` and `devDependencies`, runtime/development scope is explicit, malformed admitted declarations fail closed, and no registry, lockfile, transitive, vulnerability, license, or qualification inference is performed.

Checkpoint 7 proved the first explicit lifecycle transition. `raw-to-candidate-v1` admitted exactly one pinned PCM code unit, `src/core/associative.ts::computeAssociationWeight`, from `RAW` to `CANDIDATE` using a reproducible extraction receipt, explicit non-unknown repository-license evidence, declared-dependency evidence, and an explicit validation reference. The qualification decision and receipt are deterministic and separate from extraction evidence. The remaining 137 records stayed `RAW`; all 123 relationships remained unchanged. `CANDIDATE` is evidence-completeness admission only and is not a security, quality, legal, compatibility, suitability, or reusability conclusion.

The next bounded frontier is `TAGGING_GATE_01`: prove one evidence-backed `CANDIDATE -> TAGGED` transition for the already-admitted PCM code unit. Tagging should add useful functional and architectural classification without pretending classification is validation.

For `TAGGING_GATE_01`:

- operate first on the exact Checkpoint 7 CANDIDATE unit rather than bulk-tagging all harvested symbols
- require exact repository/revision/path/unit identity and the accepted qualification-decision/receipt chain
- define a small explicit classification vocabulary only where the target unit justifies it
- distinguish deterministic tags derived from syntax/path/relationships from interpretive functional or architectural classifications
- preserve the evidence or rationale behind every new classification and keep unknown/ambiguous dimensions explicit
- preserve disagreements rather than collapsing conflicting interpretations into a score
- keep source representation, provenance, extraction evidence, and prior qualification decision immutable
- make `TAGGED` mean classification evidence exists, not that the unit is validated, secure, compatible, or reusable
- do not jump to `VERIFIED` or `REUSABLE`
- do not introduce generic semantic ranking, vector retrieval, a broad ontology, or a generic policy engine

Likely follow-up after a proven tagging gate is a bounded `VERIFICATION_GATE_01` or `CROSS_REPO_COMPARISON_01`, chosen from demonstrated workflow need rather than roadmap momentum. A second language should be added only when a concrete target requires it.

Do not add semantic ranking, vectors, distributed infrastructure, or automatic promotion as part of the current frontier.

## Development OS routing

For durable knowledge changes, research promotion, cross-feature work, repository-memory synchronization, or DevOS changes, read `devos/AGENTS.md` and resolve the smallest branch in `devos/branches.jsonl`.

Normal repository work uses the checked-in governance projection and `.build/repoharvester-knowledge.db`. Verify it with `python tools/build_knowledge_db.py --check`; validate routing with `python tools/validate_devos.py`. Live upstream memory retrieval is limited to `devos/governance-lock.json` triggers.
