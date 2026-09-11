# Storage feature agent contract

Agents working on storage must preserve RepoHarvester's evidence/provenance boundary.

## Required behavior

- Treat GitHub repository state as implementation truth and re-check the active base before changes.
- Prefer stdlib SQLite and small deterministic interfaces until workload evidence proves a heavier database is necessary.
- Preserve exact source repository, revision, path, hashes, tags, tag ruleset, representation, and qualification state.
- Keep candidate discovery, persistence, interpretation, and qualification separate.
- Do not infer or promote qualification state during storage operations.
- Add focused tests for schema changes, identity semantics, migrations, and query behavior.
- Record meaningful bounded progress in the project checkpoint only after evidence supports it.

## Scope boundary

This feature owns local persistence and exact structured retrieval. It does not own extraction, semantic classification, source licensing decisions, reusable-code qualification, vector retrieval, or distributed services.

## Preferred loop

small patch -> focused tests -> inspect result -> record evidence -> checkpoint when warranted
