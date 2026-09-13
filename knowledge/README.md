# Knowledge Layer

The knowledge layer makes repository context searchable and queryable without replacing human-readable documents or upstream project memory.

## Runtime model

Normal repository agents use the local runtime first:

```text
versioned repo docs
        +
research source registry
        +
governance projection
        +
knowledge branch registry
        +
runtime system feedback
        ↓
.build/repoharvester-knowledge.db
```

Notion remains upstream durable RepoHarvester memory authority, but normal repo work does not require live Notion retrieval. Upstream synchronization is a separate bounded workflow under `devos/contracts/UPSTREAM_SYNC.md`.

## Files

- `sources.jsonl` — one JSON object per external research source.
- `governance_snapshot.json` — compact materialized projection of bounded upstream RepoHarvester authority/current-state claims.
- `schema.sql` — SQLite schema used by the local runtime.
- `../devos/branches.jsonl` — project-local knowledge branch registry.
- `../devos/governance-lock.json` — freshness and external-fetch trigger contract.
- `../tools/build_knowledge_db.py` — deterministic static/runtime database builder.
- `../tools/knowledge_runtime.py` — local status, authority/prevalence query, feedback, and improvement-candidate CLI.

Generated database:

```text
.build/repoharvester-knowledge.db
```

It is intentionally ignored by Git.

## Database surfaces

### Rebuildable static surfaces

- `documents` + `documents_fts`
- `sources`
- `governance_meta`
- `governance_claims` + `governance_claims_fts`
- `branch_state`

These are rebuilt from tracked repository inputs.

### Persistent local runtime surface

- `system_feedback`
- `improvement_candidates` view

Normal rebuilds preserve `system_feedback`. Use `python tools/build_knowledge_db.py --fresh` only when you intentionally want to reset local runtime feedback.

## Source registry fields

Each source record should include:

```json
{
  "id": "stable-slug",
  "title": "Human title",
  "url": "https://...",
  "kind": "code|paper|book|article|asset",
  "topics": ["..."],
  "license": "MIT|CC0|unknown|...",
  "use": "Why this matters to RepoHarvester",
  "authority": "primary|secondary|community",
  "status": "active|candidate|rejected",
  "notes": "Important boundaries"
}
```

## Governance claim contract

A projected claim records:

- stable claim ID;
- owning knowledge branch;
- statement;
- authority class;
- lifecycle/status;
- provenance source;
- verification/freshness dates;
- evidence edges;
- supersession edges.

The database derives:

- `support_count`;
- `independent_support_count`.

Those counts are **prevalence/evidence metadata only**. They can help retrieval ranking or nominate a self-improvement candidate, but they cannot upgrade authority.

## Retrieval contract

1. Live repository facts come from GitHub/current checkout.
2. Repository operating knowledge comes from accepted versioned files.
3. Durable project-memory claims already synchronized into the repo come from `governance_snapshot.json` / `governance_claims`.
4. Research sources remain evidence/reference, not automatic decisions.
5. SQLite is the normal agent runtime index, not a new independent authority.
6. A design claim should point to an ADR/design document before an agent treats it as settled.
7. Projection age alone does not invalidate a claim or create Review state.
8. If a material authority-sensitive task hits an upstream-sync trigger, follow `devos/contracts/UPSTREAM_SYNC.md`.

Useful commands:

```bash
python tools/build_knowledge_db.py
python tools/knowledge_runtime.py status
python tools/knowledge_runtime.py claims "engine"
python tools/knowledge_runtime.py candidates
```

## Self-improvement

Record concrete repository-system failures/friction with `knowledge_runtime.py feedback`. The database nominates recurrent signatures only after independent episodes recur.

Promotion remains governed by STONE/MASON and normal GitHub review/testing. The feedback table is never an authorization surface.

## Embeddings later

If semantic retrieval becomes necessary, add embeddings as a rebuildable derivative table keyed by document/claim hash. Do not move canonical knowledge into opaque vectors.
