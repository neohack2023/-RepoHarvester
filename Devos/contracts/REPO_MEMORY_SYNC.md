# Repository → Memory Sync Contract

A verified GitHub change may produce a durable RepoHarvester memory delta. It does not automatically require one.

Normal repository work uses the checked-in governance bundle and local SQLite runtime. It must not fetch Notion merely to learn ordinary current state, authority labels, branch lifecycle, or prevalence already present locally.

## Trigger after accepted repo work

Ask whether the merged/verified delta changed any of:

- current MVP/status/next action;
- durable architecture/design rule;
- shared cross-branch contract;
- feature lifecycle/status;
- accepted artifact/evidence;
- known failure/negative knowledge;
- source/provenance state;
- branch routing/dependencies;
- unresolved blocker that must survive handoff;
- repository governance bundle semantics.

If none changed, return `MEMORY_SYNC_NOOP`.

## Delta shape

```text
repository
base_sha
accepted_sha
pr_or_issue
changed_branches[]
durable_claims[]
evidence_pointers[]
negative_knowledge[]
status_changes[]
proposed_handoff_delta
proposed_branch_deltas[]
conflicts[]
uncertainty[]
local_projection_impact
```

## Rules

- Point to repository artifacts instead of copying full files.
- Preserve feature status. Merging an incubation-doc PR does not make the feature Accepted.
- Use STONE to bind evidence/provenance before any durable knowledge promotion.
- Use MASON to resolve destination, lifecycle, write authorization, and receipt.
- Update the Project Handoff only when current state, constraints, repository head, unresolved decisions, or next action materially changed.
- Do not rewrite historical receipts to reflect new state.
- Do not treat connector unavailability as evidence that local accepted repository knowledge is untrusted.
- Do not use projection age alone to create Review state.
- When upstream sync succeeds, refresh `knowledge/governance_snapshot.json`, `devos/governance-lock.json`, and the immutable sync receipt together.

## Verification

For a repo-only durable change:
- verify the exact GitHub candidate/merge identity;
- run repository tests/CI;
- verify local governance/database consistency.

For an upstream durable sync:
- follow `UPSTREAM_SYNC.md`;
- re-fetch every modified Notion target;
- bind the resulting local projection to an immutable sync receipt.

The two verification lanes are related but not interchangeable.
