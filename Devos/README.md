# RepoHarvester Development OS

`devos/` is the repository-side routing and verification layer for RepoHarvester's governed development workflow.

It adapts the existing STONE → MASON / AIOS operating model to a game project without duplicating the game's actual knowledge.

## Authority split

- **GitHub** owns live repository execution truth: code, scripts, branches, commits, issues, pull requests, tests, CI, and accepted repository documentation.
- **Notion** owns durable RepoHarvester memory: Project Handoff, hard-memory topology, branch routing, canon/decisions, lifecycle state, and memory-side evidence summaries.
- **STONE** controls source boundaries, provenance, retained/rejected receipts, uncertainty, and conflicts.
- **MASON** controls durable assembly, destination, promotion, write plans, verification, and execution receipts.
- `devos/` owns executable routing metadata and validation. It is not a third memory authority.

## Registered project

Machine-readable routing lives in `project.json`.

Scope key: `repo-harvester`
Repository: `neohack2023/repo-harvester`

The Notion bootstrap was opened through:

- `STONE-20260912-REPOHARVESTER-DEVOS-01`
- `MASON-WP-20260912-PROJECT-REPOHARVESTER-DEVOS-01`

## Knowledge topology

RepoHarvester is one durable project scope with multiple internal knowledge branches.

```text
repo-harvester
├── project-core
├── world-simulation
├── procedural-quests
├── compositional-magic
├── character-mastery
├── runtime-engine
└── tooling-agent-harness
```

A branch is a retrieval and ownership boundary, not necessarily a Git branch and not a separate project scope.

`branches.jsonl` is the repository projection of the Notion Knowledge Branch Registry. It exists so coding agents and CI can resolve a task without loading the whole project memory tree.

## Development loop

```text
request / source / repo delta
        ↓
resolve project + knowledge branch
        ↓
smallest context packet
        ↓
STONE intake when new durable knowledge is involved
        ↓
implementation / research on focused Git branch
        ↓
tests + CI + review
        ↓
merge / accepted artifact
        ↓
bounded repo→memory sync delta
        ↓
MASON assembly + destination + verification
        ↓
Project Handoff / branch memory update when warranted
        ↓
execution receipt
```

Not every code change needs a memory write. A no-op memory delta is valid.

## Folder map

```text
devos/
├── README.md
├── AGENTS.md
├── project.json
├── branches.jsonl
├── contracts/
│   ├── STONE.md
│   ├── MASON.md
│   ├── KNOWLEDGE_BRANCH.md
│   └── REPO_MEMORY_SYNC.md
├── schemas/
│   ├── branch.schema.json
│   ├── stone_manifest.schema.json
│   └── mason_plan.schema.json
├── templates/
│   └── BRANCH.md
└── receipts/
    └── README.md
```

## Agent entry

For multi-branch work, durable knowledge changes, new feature/system workspaces, research promotion, repository-memory sync, or DevOS changes:

1. read root `AGENTS.md`;
2. read `devos/AGENTS.md`;
3. resolve one branch from `branches.jsonl`;
4. enter the branch's actual GitHub surface and local `AGENTS.md` when present;
5. retrieve only explicit dependencies;
6. work on a focused Git branch/PR;
7. verify;
8. emit a memory-sync delta only for durable changes.

## Validation

```bash
python tools/validate_devos.py
python -m unittest discover -s tests -v
```

CI runs DevOS validation together with existing RepoHarvester checks.

## Growth rule

Do not create a knowledge branch merely because a topic has a page.

Create one when the topic has an independently useful retrieval boundary, durable owner, lifecycle, evidence stream, or implementation surface. Keep temporary experiments within their parent branch until that threshold is met.
