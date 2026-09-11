# Storage feature

## Problem

RepoHarvester needs a compact local persistence and exact retrieval layer for provenance-backed harvest records before broader retrieval or qualification work is justified.

## Current maturity

The feature now supports deterministic SQLite persistence plus exact structured queries. It does not add semantic search, ranking, vectors, distributed infrastructure, or automatic qualification.

## Inputs

- `HarvestRecord` values produced by the structured evidence pipeline.
- Exact source repository and source revision provenance already present on each record.
- Deterministic baseline tags and tag ruleset identifiers.

## Outputs

- A local SQLite database containing record payloads and tags.
- Stable identity keyed by repository, revision, path, and unit kind.
- Lossless reconstruction of persisted `HarvestRecord` values.
- Deterministically ordered exact query results over provenance, path/unit fields, language, qualification state, and required tags.

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

## Validation gate

The query slice is acceptable when focused tests prove exact provenance filtering, exact field filtering, all-requested-tag semantics, combined provenance/tag filtering, deterministic ordering, and empty results where exact constraints cannot all be satisfied.

## Next bounded slice

Emit compact extraction receipts that bind an ingest/store operation to repository revision, record identities/counts, ruleset, database schema version, warnings, and a reproducibility verification gate.
