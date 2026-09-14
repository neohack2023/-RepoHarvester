# Agent Router — RepoHarvester DevOS

This file governs work under `devos/` and cross-branch development orchestration for RepoHarvester.

## Lead role

`REPOHARVESTER-DEV-ORCHESTRATOR` owns task routing, branch resolution, context minimality, executor selection, cross-branch reconciliation, verification, and the final repo→memory sync delta.

It does not replace feature orchestrators such as `MAGIC-ORCHESTRATOR` or `MASTERY-ORCHESTRATOR`.

## Repository-autonomy rule

Normal repository work is self-sufficient.

Read `project.json`, `governance-lock.json`, `branches.jsonl`, and the smallest local docs/claims needed for the task. The local SQLite runtime at `.build/repoharvester-knowledge.db` materializes docs, sources, governance claims, branch state, and system feedback.

Notion pointers inside `project.json` or `branches.jsonl` are upstream provenance/synchronization targets. They are **not** instructions to fetch Notion during ordinary coding, planning, review, or branch routing.

A live upstream Notion read is allowed only through the bounded triggers in `governance-lock.json` and `contracts/UPSTREAM_SYNC.md`.

Public technical/design research is a separate capability governed by `contracts/AUTONOMOUS_RESEARCH.md`. When research preflight fires, `RESEARCH-SCOUT` may use public web/GitHub research without waiting for an additional user prompt, within the checked-in research policy and budgets.

Projection age alone:
- does not downgrade authority;
- does not mark the project Review;
- does not invalidate accepted GitHub facts;
- does not block ordinary repository work.

If the governance lock is expired, continue ordinary repo work from the local bundle. Require upstream sync only before an authority-sensitive promotion/decision that materially depends on possibly changed upstream state.

## Helper roles

- **STONE-INTAKE** — read-only source boundary, receipt harvesting, provenance, rejects, uncertainty, conflict/duplicate candidates. Cannot promote canon or write durable memory.
- **MASON-ASSEMBLER** — classifies surviving durable deltas, resolves destination/lifecycle, prepares bounded write plans and receipt material. Cannot treat inference or prevalence as authority.
- **REPO-EXECUTOR** — edits GitHub repository artifacts through focused branches/PRs and produces test/CI evidence. Cannot silently edit upstream Notion authority.
- **KNOWLEDGE-CURATOR** — maintains branch registry, local governance projection, retrieval packets, source/evidence pointers, dependency edges, feedback candidates, and drift findings.
- **RESEARCH-SCOUT** — performs bounded, need-triggered public research; separates facts, inference, and inspiration; cross-references current RepoHarvester state; and returns research receipts plus candidate opportunities. Cannot promote canon or directly authorize product changes.
- **DEVOS-QA** — validates scope isolation, registry/schema integrity, governance-lock integrity, required local agent contracts, CI evidence, and repo-memory pointer consistency.

A single coding agent may execute these roles sequentially, but must preserve their boundaries in artifacts and conclusions.

## Developer task queue

`devos/tasks.jsonl` is the repository-local assignment surface for bounded RepoHarvester development work. Read `contracts/TASK_QUEUE.md` before changing task state.

`REPOHARVESTER-DEV-ORCHESTRATOR` owns queue selection and assignment. Use `python tools/devos_tasks.py next` to inspect the highest-priority assignable task, or `python tools/devos_tasks.py next --canary` when evaluating real-work transfer.

Task queue state does not authorize work by itself. Before execution, resolve the declared `branch_keys`, load the smallest branch-local context, enter any local `AGENTS.md`, and preserve feature-orchestrator ownership. Assignment is represented by `assigned_agent` plus a lifecycle transition such as `READY → CLAIMED → IN_PROGRESS → VERIFY → DONE` through reviewed repository state.

A task reaches `DONE` only when its acceptance criteria have evidence. Transfer-canary completion may produce learning/evaluation objects, but does not grant authority or bypass STONE/MASON.

## Autonomous research scout

`devos/research-policy.json` and `contracts/AUTONOMOUS_RESEARCH.md` define the research capability. `devos/opportunities.jsonl` is the candidate opportunity ledger.

At task intake run:

```bash
python tools/research_scout.py preflight --task <REPOHARVESTER-DEV-ID>
```

Use `python tools/research_scout.py scan` to inspect active tasks that automatically warrant research. Re-run preflight with explicit signals such as `blocker`, `capability-gap`, `stale-source`, `weak-comparison`, `design-dead-end`, `external-uncertainty`, or `opportunity-window` when they arise during execution.

When preflight says research is required, the executing agent should enter `RESEARCH-SCOUT` automatically. It does **not** need to ask the user for permission to perform ordinary bounded public research. It must stay within the query/source budget, prefer primary sources for current factual claims, preserve URLs/dates/provenance, distinguish facts from inference and inspiration, and stop when additional browsing is unlikely to change the disposition.

Research may produce:
- a validated research receipt;
- zero or more candidate opportunities;
- an explicit no-op when external research does not improve the current plan.

Promising opportunities go to `devos/opportunities.jsonl`. They do not enter the developer queue or product semantics automatically. A candidate must name the RepoHarvester need it serves, cross-reference existing tasks/issues, state risks, and provide the cheapest meaningful validation. Promotion to a task, feature incubation, architecture experiment, or durable knowledge remains governed work.

## Required routing sequence

1. Resolve exact project scope from `project.json`. It must be `repo-harvester`.
2. Read `governance-lock.json`.
3. Ensure the local DB exists with `python tools/build_knowledge_db.py`.
4. If work is queue-assigned, read its row from `devos/tasks.jsonl`; otherwise classify whether a new task row is warranted.
5. Run research preflight for queue-assigned work. If it fires, execute bounded `RESEARCH-SCOUT` before committing to a solution path; record a research receipt/opportunity delta or explicit research no-op.
6. Resolve the smallest knowledge branch in `branches.jsonl`.
7. Query `python tools/knowledge_runtime.py claims "<task terms>"` when authority or current-state claims matter.
8. Load only that branch's declared GitHub surfaces plus explicit dependencies.
9. Enter a local `AGENTS.md` when the branch surface has one.
10. Classify task type: repository execution, research, feature incubation, cross-branch architecture, durable memory sync, or DevOS self-improvement.
11. Re-run research preflight if a blocker, capability gap, stale source, weak comparison, design dead-end, external uncertainty, or relevant opportunity window becomes observable.
12. If new durable knowledge is entering, apply STONE before MASON.
13. Execute repository changes through focused branch/PR/CI.
14. Emit a bounded memory-sync delta after verified work.
15. Use MASON only when the delta should change durable project memory or accepted repository operating knowledge.
16. A memory no-op is acceptable and should be stated explicitly.

## Self-improvement loop

For concrete observable failures or recurring friction, use `contracts/SELF_IMPROVEMENT.md`.

The short loop is:

```text
observed event
    ↓
system_feedback
    ↓
independent recurrence / strong verifier evidence
    ↓
STONE candidate
    ↓
MASON classification
    ↓
reviewed repository change + regression
    ↓
optional bounded upstream sync
```

Repetition never self-promotes. The system may nominate a candidate, but MASON plus normal review/test gates decide whether anything becomes an accepted rule.

## Hard constraints

- Never load sibling project memory by default.
- Never create another Project Scope Registry row for an internal RepoHarvester feature merely because it has its own feature folder.
- Never copy entire repository files into Notion hard memory as synchronization.
- Never fetch Notion merely to discover ordinary branch state, authority labels, or prevalence already represented by the local bundle.
- Never let Notion override current GitHub commit/PR/CI facts.
- Never let GitHub execution implicitly rewrite durable Notion canon/handoff state.
- Never promote research to canon because it appears in a polished document.
- Never let a research opportunity directly mutate product code or become a backlog task without the normal routing/governance path.
- Never perform unbounded crawling or research for novelty's sake; research must name the active RepoHarvester need or capability gap.
- Never treat an inspiration/community source as factual authority without stronger evidence appropriate to the claim.
- Never let high prevalence/repetition upgrade authority.
- Never bypass feature-local orchestrators for feature-owned semantics.
- Never use one global context packet when a branch packet can answer the task.
- Preserve RepoHarvester's deterministic evidence tests and existing lifecycle gates.

## Cross-branch changes

When a change touches more than one branch:

- name every affected branch;
- preserve each branch's evidence separately;
- identify shared contract deltas;
- route shared decisions through `project-core`;
- update branch dependencies when the coupling becomes durable;
- require `DEVOS-QA` validation before claiming the topology is stable.

## Evidence contract

Substantial DevOS work should state:

- resolved scope;
- resolved knowledge branch(es);
- source boundary;
- local governance snapshot/claim(s) used;
- research preflight disposition and any receipt/opportunity refs;
- implementation/research delta;
- affected authority surface;
- tests/CI run;
- durable memory-sync delta or explicit no-op;
- observable system-feedback event(s), if any;
- unresolved drift/conflicts.

## Verification

Run:

```bash
python tools/validate_devos.py
python tools/build_knowledge_db.py --check
python tools/research_scout.py validate-opportunities
python -m unittest discover -s tests -v
```

Run the pinned external acceptance workflow when harvesting behavior changes.
