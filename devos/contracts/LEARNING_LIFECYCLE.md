# DevOS Persisted Learning Lifecycle

Status: **candidate executable slice**

This contract extends the executable learning threshold from PR #42 into durable local lifecycle state without widening authority.

## Path

```text
reasoned solution
→ validated procedure
→ reusable capability
→ held-out transfer
→ consolidated experience
→ persisted capability history
→ replay / re-evaluation
```

## Memory classes

- `EPISODIC`: what happened in one bounded execution.
- `SEMANTIC`: an evidence-backed lesson candidate.
- `PROCEDURAL`: a procedure-linked reusable skill representation.
- `NEGATIVE`: a known failure mode or rejected strategy.

Every consolidated record requires addressable evidence. Procedural memory additionally requires a procedure identity.

## Persistence model

The local learning store persists:

- procedure specifications;
- evaluation reports;
- consolidated experience records;
- current capability snapshots;
- immutable capability lifecycle events.

Capability snapshots may advance as new evaluation evidence arrives. History remains queryable so `REFLECTION → TRANSFER` is an observable transition rather than a silently overwritten label.

## Separation laws

- Persistence does not increase authority.
- `TRANSFER` is engineering maturity, not permission to mutate code or memory.
- Evidence references remain attached to consolidated experience.
- Procedure rollback references remain part of the persisted procedure contract.
- Capability lifecycle events retain `authority_effect=NONE` and `promotion_state=CANDIDATE_ONLY`.
- Curriculum selection, optimizer mutation, and post-change causal promotion are outside this slice.

## Promotion boundary

```text
local learning state
→ evaluation evidence
→ STONE
→ MASON
→ focused repository change
→ CI
→ canary when warranted
```

No local learning table is an authority table.

## Follow-up

After persistence/replay is proven in CI and on real development work, the next candidate slice may use capability gaps plus active product priorities to nominate bounded curriculum targets. Curriculum should remain recommendation-only until transfer and canary evidence demonstrate useful acceleration without scope or authority drift.
