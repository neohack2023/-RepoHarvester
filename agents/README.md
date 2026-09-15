# RepoHarvester agent coordination hub

This directory is the shared coordination surface for human and AI contributors working under the repository contract in `/AGENTS.md`.

It does not replace feature-local contracts. Work inside `features/<feature>/` must still follow that feature's `AGENTS.md` and `FEATURE.md`.

## Authority order

1. GitHub `main` is the implementation source of truth.
2. `/AGENTS.md` defines repository-wide rules.
3. `features/<feature>/AGENTS.md` narrows those rules for a bounded feature cell.
4. A task dossier records the current assignment, scope, evidence targets, and handoff state.
5. Agent notes, handoffs, and receipts never override code, tests, checkpoints, or repository contracts.

No agent role grants independent merge authority or permission to widen scope.

## Coordination layout

```text
agents/
├── README.md
├── REGISTRY.yaml
├── PROTOCOL.md
├── tasks/
│   └── TASK_TEMPLATE.md
├── handoffs/
│   └── HANDOFF_TEMPLATE.md
└── receipts/
    └── README.md
```

## Why task dossiers are separate files

Do not use one giant shared work queue as mutable state. Parallel agents editing the same queue creates avoidable conflicts and makes ownership ambiguous.

Use one file per bounded task under `agents/tasks/`. The task file is the coordination record for that slice. It should name the feature cell, allowed paths, forbidden paths, required evidence, current owner, reviewers, and exact base revision.

Suggested task name:

```text
agents/tasks/TASK_<short-id>_<slug>.md
```

Examples:

```text
TASK_TAGGING_GATE_01_pcm_candidate.md
TASK_TS_CONFIG_RESOLUTION_01.md
```

## Handoffs

A handoff is required when ownership changes or when one role completes work needed by another role. Handoffs belong under `agents/handoffs/` and should reference the task dossier and exact commit or branch state.

A handoff is not a checkpoint. A checkpoint is recorded only when the repository's acceptance requirements are satisfied.

## Receipts

Coordination receipts under `agents/receipts/` are lightweight evidence pointers for agent work such as commands run, tests executed, reviewed commits, and validation results.

They do not replace product-level provenance, extraction receipts, qualification receipts, or `CHECKPOINT.md`.

## Default working rhythm

Use this sequence unless a feature contract is stricter:

```text
read authority -> resolve exact base -> claim bounded task -> work only inside scope
-> run focused validation -> write receipt -> hand off for review -> checkpoint when warranted
```

Parallel work is encouraged only when task dossiers have non-overlapping write scopes or an explicit integration owner is named.
