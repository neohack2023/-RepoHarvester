# Agent coordination protocol

This protocol coordinates bounded parallel work. It does not create an autonomous orchestration layer and does not replace repository or feature contracts.

## 1. Resolve authority before work

Before claiming a task:

- read `/AGENTS.md`
- read the relevant `features/<feature>/AGENTS.md` and `FEATURE.md` when one exists
- inspect the current `main` head
- inspect `CHECKPOINT.md`
- record the exact base revision in the task dossier

## 2. Claim one bounded task

Create or update one task dossier under `agents/tasks/`.

A valid task dossier must state:

- task ID and objective
- lifecycle state
- exact base revision
- owner role
- reviewer role or roles
- feature cell
- allowed write paths
- forbidden write paths
- acceptance evidence
- dependencies and handoff requirements

The task scope is a hard boundary. Discoveries outside scope become follow-up candidates rather than silent expansion.

## 3. Parallelism rules

Parallel agents may proceed when either:

- their allowed write paths do not overlap, or
- the task dossier names one integration owner and explains the overlap

Agents should not edit one shared mutable queue to claim work. One task file per slice is the coordination primitive.

## 4. Evidence before claims

Implementation claims should be backed by the narrowest useful evidence, such as:

- exact commit or branch revision
- focused test command and result
- deterministic fixture output
- schema or receipt validation
- compatibility check
- external source revision when research is involved

Store lightweight coordination evidence under `agents/receipts/` when it helps another agent reproduce the work.

## 5. Handoff

Create a handoff when ownership changes between roles or agents.

The handoff must include:

- source task ID
- sender role
- receiving role
- exact branch or commit state
- completed work
- unresolved findings
- files changed
- tests or checks run
- next bounded action

Do not describe speculative future work as completed.

## 6. Review and checkpoint

The reviewer compares the implementation and evidence against the task dossier and repository contracts.

A task can be recommended for checkpoint only when its acceptance evidence is satisfied. `CHECKPOINT.md` remains the repository record for proven implementation milestones.

## Lifecycle vocabulary

Use these coordination states unless a narrower feature contract defines more detail:

```text
PROPOSED -> CLAIMED -> IMPLEMENTING -> REVIEW -> READY -> CLOSED
```

Use `BLOCKED` when progress cannot continue without a concrete dependency or decision. Use `SUPERSEDED` when a newer task replaces the slice.
