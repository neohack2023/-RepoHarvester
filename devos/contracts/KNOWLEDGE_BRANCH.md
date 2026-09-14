# Knowledge Branch Contract

A RepoHarvester knowledge branch is a retrieval, ownership, evidence, and lifecycle boundary inside the single `repo-harvester` scope.

It is not automatically:

- a Git branch;
- a separate Notion project scope;
- a feature accepted for production;
- a reason to duplicate documents.

## Required fields

Every row in `devos/branches.jsonl` defines:

- `branch_key` — stable machine key;
- `status` — active/incubating/candidate/paused/archived/superseded;
- `branch_type` — core/feature/simulation/runtime/tooling/research;
- `owner_agent` — routing owner;
- `github_paths` — smallest repository surfaces for normal retrieval;
- `notion_page` — durable branch pointer;
- `dependencies` — other RepoHarvester branches permitted in the context packet;
- `exclusions` — explicit suppression rules;
- `retrieval_packet` — named Notion packet recipe;
- `tracking` — issue/PR identifiers when useful.

## Creation threshold

Create a branch only when the topic has an independently useful retrieval boundary, durable owner, lifecycle, evidence stream, implementation surface, or specialist agent contract.

Do not create branches for one chat, one experiment, one source, one issue, or one temporary task.

## Cross-branch law

A local branch may make local candidate decisions. A decision that changes another branch's semantic or compatibility contract must identify the dependency and route the shared delta through `project-core`.

## Feature branch law

Feature-local `AGENTS.md` and orchestrators remain authoritative for feature semantics. DevOS routes into them; it does not replace them.

## Drift

GitHub current files/issues/PRs/CI win for execution facts. Notion branch records win for durable routing/lifecycle until a governed update changes them.

A mismatch is drift to report, not permission to silently merge authorities.
