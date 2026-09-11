# Storage feature

## Problem

RepoHarvester needs a compact local persistence and exact retrieval layer for provenance-backed harvest records before broader retrieval or qualification work is justified.

## Current maturity

The feature now supports deterministic SQLite persistence, exact structured queries, and compact extraction receipts that bind stored records back to one exact repository revision. It does not add semantic search, ranking, vectors, distributed infrastructure, or automatic qualification.

## Inputs

- `HarvestRecord` values produced by the structured evidence pipeline.
- Exact source repository and source revision provenance already present on each record.
- Deterministic baseline tags and tag ruleset identifiers.

## Outputs

- A local SQLite database containing record payloads and tags.
- Stable identity keyed by repository, revision, path, and unit kind.
- Lossless reconstruction of persisted `HarvestRecord` values.
- Deterministically ordered exact query results over provenance, path/unit fields, language, qualification state, and required tags.
- Canonical extraction receipts containing repository/revision, record count, manifest hash, tag rulesets, qualification states, schema version, warnings, and next gate.

## Non-goals

- LLM-generated tags or interpretation.
- Fuzzy or semantic matching.
- Ranking or relevance scores.
- Automatic promotion beyond the record's supplied qualification state.
- Vector search or distributed storage.
- Copying harvested source repositories.

## Deterministic operations

- Schema creation and versioning.
- Record upsert by exact source identity.
- Tag normalization to unique sorted rows.
- Exact reconstruction of stored record values.
- AND-filtered exact provenance and tag retrieval.
- Canonical manifest hashing and receipt verification.

## Validation gate

This storage/evidence slice is acceptable when focused tests prove lossless persistence, idempotent identity semantics, exact retrieval, deterministic ordering, receipt order independence, manifest drift detection, receipt file round-trip, and successful reproduction against records loaded back from SQLite.

## Next bounded slice

Run one real external repository through the complete ingest -> record -> tag -> store -> query -> receipt path at an exact revision, capture the resulting evidence, and repair only defects demonstrated by that acceptance run.
