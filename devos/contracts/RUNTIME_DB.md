# DevOS Runtime Database Contract

Status: **Runtime DB v2 candidate implementation**  
Tracks: Issue #51

## Purpose

`.build/repoharvester-knowledge.db` is RepoHarvester DevOS's single repository-local operational database. It exists to make repository knowledge, queue state, research, evidence, and learning history queryable without turning the database itself into project authority.

Git-reviewed repository artifacts remain the declaration and review surface. SQLite is their local operational projection plus the durable local runtime for append-only evidence/learning state.

## Storage boundary

### Rebuildable repository projection

Normal `python tools/build_knowledge_db.py` refreshes repository-derived state including:

- documentation and FTS indexes;
- research source registry;
- governance projection;
- knowledge branch registry;
- developer task manifests and task edges;
- research opportunity manifests and edges;
- checked-in research receipts and their source/task/branch edges.

These rows can be reconstructed from accepted repository artifacts.

### Preserved runtime history

Normal rebuilds must preserve runtime-generated history including:

- system feedback;
- evidence roots, atomic findings, assessments, triangulation batches, and evidence delta packets;
- learning procedures, evaluations, experiences, capabilities, and capability lifecycle events;
- normalized evidence/capability graph edges derived from those runtime records.

`--fresh` is the explicit destructive path that removes the local database, WAL, and shared-memory files before rebuilding.

## Connection policy

All DevOS Python code that mutates or queries the operational runtime should open SQLite through `tools/db_runtime.py` rather than creating ad-hoc policy.

The file-backed runtime uses:

```text
foreign_keys = ON
busy_timeout = 5000 ms
journal_mode = WAL
synchronous = NORMAL
```

WAL improves local reader/writer overlap but does not make SQLite a multi-writer server. Transactions should remain short. One writer at a time remains an expected SQLite constraint.

`python tools/knowledge_runtime.py status` exposes the effective SQLite library version, schema version, `user_version`, journal mode, foreign-key state, busy timeout, and synchronous mode so operating assumptions remain observable.

## Migration law

Database shape evolves through deterministic, ordered migrations in `tools/db_runtime.py`.

- `knowledge/schema.sql` is the frozen Runtime DB v1 baseline for migration/bootstrap purposes.
- `schema_migrations` records migration version, name, checksum, and application time.
- Migration identity/checksum mismatches fail closed.
- Re-opening an already migrated database is idempotent.
- Compatibility migrations must cover existing populated runtime databases, not only empty installs.
- `PRAGMA user_version` mirrors the current DevOS runtime schema version for inspection, but `schema_migrations` is the migration ledger.

Do not rewrite the v1 baseline to represent later runtime versions. Add a migration instead.

## Graph normalization law

JSON remains appropriate for complete immutable payloads and receipts. Relationships used frequently for routing, joins, lifecycle inspection, or provenance should also be materialized as rows.

Runtime DB v2 normalizes hot relationships such as:

- task → branch;
- task → dependency;
- opportunity → task/branch/source/evidence;
- research episode → task/branch/source;
- finding → evidence root;
- procedure/experience → evidence ref;
- capability → procedure;
- capability → transfer fixture.

The JSON envelope is retained. Normalization is an access/indexing optimization, not an authority transformation.

## Learning lifecycle chronology

Capability lifecycle history is append-oriented and explicitly chronological. Events record:

- `created_at`;
- per-capability `event_sequence`;
- `episode_id` when available;
- `predecessor_event_id`;
- evaluator version.

Legacy event histories without chronology are upgraded once using the best available local insertion order and marked with explicit migrated chronology rather than continuing to sort by content hash.

## Index policy

Index observed access patterns rather than every field. Runtime DB v2 includes targeted indexes for branch/procedure/capability/evidence lookup and partial indexes for hot lifecycle subsets such as assignable tasks, candidate opportunities, and open system feedback.

After schema/index work and repository projection rebuilds, run `PRAGMA optimize` through the shared runtime.

## Authority boundary

Database persistence, indexing, query frequency, and relation count never increase authority.

Learning, reflection, research, and opportunity objects remain subject to their owning contracts. In particular, `authority_effect=NONE` and `promotion_state=CANDIDATE_ONLY` remain intact until governed promotion occurs through normal RepoHarvester gates.

## When SQLite stops being enough

Feature count alone is not a database migration trigger. SQLite remains the preferred local DevOS runtime while one repository checkout/host owns mutable operational state.

Reconsider a server database only when DevOS requires multiple hosts or machines to concurrently mutate a shared live runtime, or another measured constraint demonstrates SQLite is the bottleneck. Such a change requires a separate architecture decision and migration plan.

## Verification

Runtime DB changes must verify at least:

- clean bootstrap;
- repeated/idempotent migration;
- upgrade from a populated prior schema where relevant;
- connection PRAGMA enforcement;
- manifest materialization and normalized edges;
- preservation of runtime history across normal rebuild;
- learning lifecycle chronological ordering;
- full DevOS/unit CI.
