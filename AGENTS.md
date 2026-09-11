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

State transitions must eventually be backed by explicit evidence and admission rules. Storage or extraction operations must not infer promotion by themselves.

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
- `features/code-units/` — deterministic symbol/code-unit extraction frontier

## Current frontier

Checkpoint 1 proved one external repository can be ingested, represented as provenance-backed RAW file records, deterministically tagged, stored in SQLite, exactly queried, reproduced, and accompanied by an extraction receipt without modifying the source repository.

The next bounded frontier is `CODE_UNIT_EXTRACTION_01` under `features/code-units/`.

Do not add semantic ranking, vectors, distributed infrastructure, or automatic qualification as part of that slice.
