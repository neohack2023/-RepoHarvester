# MASON Assembly Contract — RepoHarvester

MASON consumes only a locked STONE package when durable RepoHarvester knowledge may change.

MASON decides what surviving knowledge becomes, where it belongs, whether it is strong enough to promote, and how a write is verified.

Repository-local operation is supported. Lack of live Notion access does not force a Review state when the required upstream authority is already represented by the checked-in governance bundle.

## Intake classification

Preserve authority labels such as:

- `USER_LOCKED_AUTHORITY`
- `RATIFIED_SYSTEM_AUTHORITY`
- `ACCEPTED_ARTIFACT_EVIDENCE`
- `REPEATED_ACCEPTED_EVIDENCE`
- `OBSERVED_RUNTIME_EVIDENCE`
- `SOURCE_BACKED_RESEARCH`
- `CANDIDATE_INFERENCE`
- `CONFLICTED`
- `SUPERSEDED`
- `REJECTED`

Usefulness, freshness, confidence, and prevalence are separate from authority. None automatically upgrades authority.

## Two durable destinations

MASON distinguishes:

### Repository-accepted knowledge

Versioned operating knowledge whose authority domain is the repository, such as:

- agent routing;
- repository review/test law;
- tooling behavior;
- negative knowledge/regression guards;
- local development procedures;
- local materialized governance projection.

Repository-accepted knowledge may be promoted through reviewed GitHub changes plus applicable tests/CI without requiring a live Notion read.

### Upstream RepoHarvester memory

Project-wide canon, durable handoff state, cross-session project decisions, memory lifecycle, or Notion branch state.

These remain Notion-governed. A repo agent may prepare a bounded sync delta, but it must not pretend the upstream write occurred. Use `UPSTREAM_SYNC.md` and `REPO_MEMORY_SYNC.md`.

## RepoHarvester destinations

- Project-wide durable doctrine → Notion `01_CANON` plus accepted GitHub ADR/reference when implementation-facing.
- Shared project decisions → Notion `03_DECISIONS` + GitHub ADR/PR pointer.
- Branch-specific knowledge → matching project branch and matching GitHub feature/system surface.
- Repository operating law → versioned repo contract/rule plus tests.
- Evidence → `04_EVIDENCE` with exact GitHub/test/playtest pointers when upstream persistence is required.
- Research → `05_RESEARCH` / repository research docs with provenance and candidate state.
- Accepted outputs → `06_ARTIFACTS` pointers.
- Sources → `07_SOURCES` + `knowledge/sources.jsonl` when repository tooling needs them.
- Execution receipts → global MASON Episode Ledger, with RepoHarvester `08_EXECUTION` as a pointer/index surface.
- Current state/next action → Project Handoff only.
- Self-improvement candidates → remain local candidates until promotion gates in `SELF_IMPROVEMENT.md` close.

## Memory card rule

Create atomic durable units only when independently retrievable. Do not promote a whole feature workspace as one giant memory object.

## Canon gate

Project-wide canon requires at least one of:

1. explicit user lock/correction;
2. repeated accepted evidence;
3. accepted artifact whose operation depends on the rule;
4. already-ratified project authority reinforced by new evidence.

Feature incubation documents remain Candidate/Incubating until their own promotion gates close.

High prevalence by itself is never a canon gate.

## Write plan

Every durable mutation plan must name:

- source STONE manifest;
- exact target(s);
- exact delta;
- authority effect;
- preconditions/freshness checks;
- whether the target is repo-local or upstream memory;
- rollback/failure behavior;
- verification method;
- required authorization.

## Repository-only completion

When a repository-local rule is accepted but upstream memory also ought to change:

1. finish and verify the repository change;
2. emit a bounded `UPSTREAM_SYNC_REQUIRED` / memory-sync delta;
3. keep the local accepted rule usable in its repository authority domain;
4. do not downgrade it merely because the upstream connector is unavailable;
5. do not claim Notion canon changed until the explicit sync succeeds.

## Receipt

One execution attempt receives one immutable receipt after writes stop and independent verification completes.

A no-op durable result is valid.
