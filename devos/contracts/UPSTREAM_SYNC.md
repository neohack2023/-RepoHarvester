# Upstream Governance Synchronization

This is the bounded synchronization path between RepoHarvester's self-sufficient repository governance bundle and upstream Notion project memory.

Normal repository work must remain local. Do not invoke this process merely for orientation.

## Trigger gate

Proceed only when at least one condition from `devos/governance-lock.json` is true:

1. the owner explicitly requests upstream synchronization;
2. a cross-project/global governance change is known to affect RepoHarvester;
3. a material authority conflict cannot be resolved from the local bundle;
4. a material task requires an upstream claim absent from the bundle;
5. the governance lock is expired **and** an authority-sensitive promotion/decision depends on current upstream state.

Lock expiry alone does not block normal coding, testing, review, or use of accepted repository facts.

## Pinned RepoHarvester upstream set

Read only the project-specific objects already registered in `devos/project.json` unless stronger owner direction changes the set:

- RepoHarvester Project Handoff;
- RepoHarvester Scope Registry record;
- RepoHarvester Knowledge Branch Registry;
- specific canon/decision/evidence pages named by the bounded sync delta.

Do not browse sibling project memory.

## Compare delta only

Compare repository-relevant semantics against:
- `knowledge/governance_snapshot.json`;
- accepted repository artifacts;
- `devos/branches.jsonl`;
- the proposed memory-sync delta.

Classify the result as exactly one of:

- `NO_MATERIAL_DELTA`
- `MATERIAL_DELTA_RECONCILED`
- `MATERIAL_DELTA_PENDING`

For each material delta, record:
- upstream position;
- repository position;
- authority domain;
- bounded reconciliation or unresolved decision;
- affected branch/files.

## Projection refresh

After a complete successful sync:

1. update the compact `knowledge/governance_snapshot.json`;
2. recompute its SHA-256;
3. write one immutable JSON receipt under `devos/sync/receipts/`;
4. bind receipt path + SHA-256 and projection SHA-256 in `devos/governance-lock.json`;
5. advance `valid_through` by exactly `sync_freshness_days` only for `NO_MATERIAL_DELTA` or `MATERIAL_DELTA_RECONCILED`;
6. rebuild/check the local knowledge DB;
7. run DevOS validation and tests.

If any pinned required source cannot be resolved, or the result is `MATERIAL_DELTA_PENDING`, do not renew freshness.

## Authority boundary

A synchronization refresh is evidence of bounded reconciliation. It is not an authority cutover.

- GitHub remains live repository execution authority.
- Notion remains upstream durable RepoHarvester memory authority.
- The local projection remains the repository runtime context for normal agents.
- Prevalence/support counts remain separate from authority.
