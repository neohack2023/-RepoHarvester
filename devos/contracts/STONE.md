# STONE Intake Contract — RepoHarvester

STONE is the source-boundary and evidence gate for durable RepoHarvester knowledge.

It is **not** required for every transient code edit. It is required when new material may become durable project memory, change shared knowledge, feed MASON, or enter the DevOS self-improvement loop.

This file is the operational STONE contract for repository agents. The registered Notion STONE skill is upstream provenance/governance reference only; normal repo work does not require live Notion access.

## Local runtime inputs

Before STONE intake, prefer local evidence:

- exact source object or bounded episode;
- requested transformation;
- resolved `repo-harvester` scope from `devos/project.json`;
- target knowledge branch from `devos/branches.jsonl`;
- applicable governance claims from `.build/repoharvester-knowledge.db`;
- included artifacts;
- excluded sources;
- live repository facts when relevant;
- observable system-feedback events when the episode is about DevOS improvement.

A live Notion read is not a missing prerequisite if the required authority/state is already materialized in the local governance bundle.

## Output

A locked manifest with:

```text
stone_manifest_id
source_identity
episode_boundary
requested_transformation
resolved_scope
knowledge_branches[]
included_artifacts[]
excluded_sources[]
retained_receipts[]
rejected_receipts[]
duplicate_candidates[]
conflict_candidates[]
unresolved_questions[]
provenance_map
integrity_digest
completion_state
```

## Retain

- direct user decisions/corrections;
- merged/accepted artifacts;
- observed test/CI/playtest results;
- durable design or engineering constraints;
- reusable project methods;
- failures/negative knowledge that changes future work;
- unresolved blockers that must survive handoff;
- evidence/source pointers;
- authority/lifecycle decisions;
- repeated repository-system friction with concrete evidence.

## Reject or keep transient

- conversational glue;
- duplicate explanation;
- assistant confidence/praise;
- unsupported certainty;
- hidden reasoning;
- abandoned drafts without a reusable lesson;
- sibling-project material outside the explicit boundary;
- speculative associations presented as fact;
- projection age by itself as evidence of invalidity.

## Authority/prevalence separation

STONE may record support frequency and independent recurrence. It must not convert recurrence into stronger authority.

Examples:

- ten model suggestions remain model suggestions;
- two independent CI-backed failures may justify a promotion **candidate**;
- a direct user lock remains stronger authority even if it appears once;
- a stale timestamp does not defeat a stronger still-applicable authority source by itself.

## Lock gate

STONE locks only when source, boundary, requested transformation, scope, target branch, provenance, rejects, conflicts, and uncertainty are explicit.

If not, return `STONE_UNLOCKED` and do not let MASON silently repair the package by importing extra context.

When an upstream governance conflict is material and cannot be resolved from the local bundle, stop with `UPSTREAM_SYNC_REQUIRED` and route through `UPSTREAM_SYNC.md`. Do not perform free-form Notion browsing.
