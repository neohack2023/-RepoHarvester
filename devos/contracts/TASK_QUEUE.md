# DevOS Developer Task Queue Contract

`devos/tasks.jsonl` is the repository-local assignment surface for bounded RepoHarvester development work.

It is owned by `REPOHARVESTER-DEV-ORCHESTRATOR` and does not replace GitHub issues, feature-local orchestrators, STONE/MASON, or branch-specific `AGENTS.md` contracts.

## Purpose

The task queue exists so DevOS can select, assign, execute, verify, and learn from real product work without regenerating the backlog from prose every session.

Each row is one task with a stable identity and explicit routing/evidence boundaries.

## Required fields

- `task_id`: immutable `REPOHARVESTER-DEV-NNN` identity.
- `title`: compact developer-facing title.
- `priority`: positive integer; lower is earlier.
- `status`: one of `READY`, `BLOCKED`, `TRACKING`, `CLAIMED`, `IN_PROGRESS`, `VERIFY`, `DONE`, `PAUSED`, `REJECTED`.
- `branch_keys`: one or more branch keys from `devos/branches.jsonl`.
- `task_type`: `repository_execution`, `feature_incubation`, `quality_assurance`, `research`, `cross_branch_architecture`, or `devos_self_improvement`.
- `owner_role`: routing owner. Cross-feature semantics must still defer to the feature-local orchestrator.
- `assigned_agent`: null until explicitly assigned, then a repository agent/role identifier.
- `depends_on`: task IDs that must be `DONE` before normal assignment.
- `tracking`: related GitHub issue/PR references.
- `objective`: bounded outcome.
- `acceptance`: deterministic or inspectable completion criteria.
- `transfer_canary`: whether successful execution is intended to provide real-work transfer evidence for the DevOS learning lifecycle.
- `evidence_refs`: provenance pointers for why the task exists or what governs it.

## Assignment law

`REPOHARVESTER-DEV-ORCHESTRATOR` assigns work from this queue.

A task is normally assignable only when:

1. `status == READY`;
2. every `depends_on` task is `DONE`;
3. all `branch_keys` resolve in `devos/branches.jsonl`;
4. the smallest branch-local context has been loaded;
5. feature-owned semantics are routed through that feature's orchestrator;
6. the task is still aligned with the active product frontier;
7. autonomous research preflight has been evaluated under `devos/contracts/AUTONOMOUS_RESEARCH.md`.

Run:

```bash
python tools/research_scout.py preflight --task <REPOHARVESTER-DEV-ID>
```

If research preflight fires, `RESEARCH-SCOUT` may perform bounded public research without a separate user prompt, then return a research receipt plus candidate opportunities or an explicit no-op. Research expands the option set; it does not authorize a solution, feature, or queue mutation by itself.

Assignment changes `assigned_agent` and moves the task to `CLAIMED` or `IN_PROGRESS` through a reviewed repository change. The queue is not a distributed lock service; concurrent agents must still reconcile through Git/PR state.

## Research-opportunity handoff

`devos/opportunities.jsonl` is an intake ledger for need-bound ideas returned by `RESEARCH-SCOUT`.

An opportunity may become queue work only after it has:
- a named RepoHarvester need or capability gap;
- source/evidence provenance;
- cross-reference against current tasks/issues/decisions;
- explicit risks and a bounded validation plan;
- a disposition such as `PROPOSE_TASK`, `PROPOSE_FEATURE_INCUBATION`, or `PROPOSE_EXPERIMENT`;
- normal orchestrator/governance review.

Do not let the scout append production tasks simply because an external technique looks promising. Prefer strengthening an existing task over creating a duplicate.

## Completion law

A task may move to `DONE` only after its acceptance criteria are evidenced. Substantial work must include the DevOS evidence contract: resolved scope/branches, source boundary, research preflight/receipt disposition, implementation delta, tests/CI, memory-sync delta or no-op, and unresolved conflicts.

A completed transfer canary may create evaluation/experience/capability evidence. It does **not** gain authority merely because it passed. Learning objects remain authority-neutral and durable promotion still routes through STONE/MASON.

## Dependency law

Dependencies are task identities, not vague prose. `BLOCKED` tasks should name the task(s) that unblock them. `TRACKING` tasks can mirror an existing external decision or milestone without becoming duplicate implementation work.

Cycles are invalid.

## Selection policy

`python tools/devos_tasks.py next` returns the highest-priority currently assignable task. This is a deterministic convenience, not autonomous authorization to start or merge work.

When several tasks are equally eligible, sort by numeric priority then `task_id`.

## Real-work transfer policy

Prefer `transfer_canary=true` tasks when the current goal is evaluating DevOS transfer. A useful canary must advance RepoHarvester even if the learning experiment fails.

The initial top canary is `REPOHARVESTER-DEV-001`: save-game schema migration + deterministic replay.
