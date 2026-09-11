# Storage feature

## Problem

RepoHarvester needs a compact local persistence layer for provenance-backed harvest records before broader retrieval or qualification work is justified.

## Current maturity

This feature begins with deterministic SQLite persistence. It does not add semantic search, vectors, distributed infrastructure, or automatic qualification.

## Inputs

- `HarvestRecord` values produced by the structured evidence pipeline.
- Exact source repository and source revision provenance already present on each record.
- Deterministic baseline tags and tag ruleset identifiers.

## Outputs

- A local SQLite database containing record payloads and tags.
- Stable identity keyed by repository, revision, path, and unit kind.
- Lossless reconstruction of persisted `HarvestRecord` values.

## Non-goals

- LLM-generated tags or interpretation.
- Automatic promotion beyond the record's supplied qualification state.
- Vector search or distributed storage.
- Copying harvested source repositories.

## Deterministic operations

- Schema creation and versioning.
- Record upsert by exact source identity.
- Tag normalization to unique sorted rows.
- Exact reconstruction of stored record values.

## Validation gate

The slice is acceptable when focused tests prove full-field round-trip, idempotent replacement at the same source identity, distinct revision/path retention, and schema versioning without changing existing extraction behavior.

## Next bounded slice

Add exact provenance/tag query filters over persisted records without adding ranking or semantic interpretation.
