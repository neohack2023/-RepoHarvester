# DevOS Autonomous Research Scout

Status: **Candidate implementation contract**  
Tracks: Issue #49

## Purpose

`RESEARCH-SCOUT` gives RepoHarvester a bounded curiosity loop. It may recognize when a task, capability gap, branch decision, or design problem needs outside knowledge and perform public research without waiting for a user to explicitly request research.

The scout exists to improve RepoHarvester, not to maximize novelty.

## Operating law

> Need triggers research. Research produces evidence and possibilities. Evaluation decides usefulness. Governance decides adoption.

Research findings, analogies, and proposed features are learning inputs. They are not project authority.

Every scout artifact must preserve:

```text
authority_effect = NONE
promotion_state = CANDIDATE_ONLY
```

## Role boundary

`RESEARCH-SCOUT` is a helper role under `REPOHARVESTER-DEV-ORCHESTRATOR`.

It may:
- inspect the active task, branch packet, capability gaps, and known failures;
- decide that bounded public research is warranted;
- search public web sources, public source repositories, standards, papers, engine/browser documentation, game-development postmortems, conference material, and community discussions;
- cross-reference findings against current RepoHarvester state;
- produce research receipts and opportunity candidates;
- recommend a task, experiment, feature incubation, architecture comparison, or explicit no-op.

It may not:
- promote a finding to canon;
- silently change product semantics;
- merge code because an external project uses a technique;
- treat community popularity as evidence of correctness;
- crawl indefinitely;
- add a feature only because it is novel;
- bypass feature orchestrators, the task queue, STONE/MASON, PR review, CI, or canary evaluation.

## Autonomous triggers

The orchestrator should run research preflight at task intake and may rerun it when new signals appear.

Research is warranted when one or more of these conditions are present:

1. **External uncertainty** — current browser, engine, API, platform, licensing, performance, or tooling behavior materially affects the task.
2. **Blocker** — progress is blocked by an unknown outside the repository.
3. **Capability gap** — DevOS evaluation shows repeated failure or insufficient transfer and external approaches may offer useful patterns.
4. **Stale evidence** — an important external source is older than the policy freshness window for its claim type.
5. **Weak comparison** — a consequential decision lacks meaningful alternatives or comparative evidence.
6. **Design dead-end** — the current design satisfies mechanics but is producing poor usability, performance, expressive range, or maintainability.
7. **Feature incubation** — a new gameplay/system design would benefit from studying successful and failed analogues before implementation.
8. **Opportunity window** — a relevant new technique, browser capability, engine feature, open-source system, paper, or postmortem could materially improve an active RepoHarvester milestone.

Research is not warranted merely because the scout can find something interesting.

## Research preflight

Use:

```bash
python tools/research_scout.py preflight --task REPOHARVESTER-DEV-001
```

Additional observed signals can be supplied without changing task metadata:

```bash
python tools/research_scout.py preflight --task REPOHARVESTER-DEV-001 --signal blocker --signal capability-gap
```

The preflight output is deterministic for the same repository state, policy, task, and explicit signals. It states whether research is warranted, why, the bounded query/source budget, and the research lanes to cover.

## Source classes

Factual claims and inspiration are deliberately separated.

### Evidence-oriented sources
Prefer, in order appropriate to the claim:
- standards/specifications;
- primary browser/engine/tool documentation;
- source repositories and release notes;
- peer-reviewed or first-party research papers;
- maintainer engineering notes;
- reproducible benchmarks with inspectable methodology.

Current API behavior, engine-version capability, browser constraints, licensing, and policy claims require a primary source whenever practical.

### Inspiration-oriented sources
Useful for idea generation but not factual authority:
- game-development postmortems;
- conference talks;
- design analyses;
- public demos and open-source games;
- community discussions;
- player/developer anecdotes.

An inspiration source can motivate a candidate. It cannot by itself prove that the candidate will work in RepoHarvester.

## Research lanes

A normal bounded scout should cover several complementary lanes rather than one giant query:

```text
CURRENT STATE       primary docs / standards / release behavior
IMPLEMENTATIONS     source repos / concrete systems
FAILURE MODES       postmortems / bugs / limitations / counterexamples
ADJACENT DESIGN     analogous games / systems / techniques
OPPORTUNITY         new capability or feature candidate tied to an RepoHarvester need
```

Not every run needs every lane. The preflight plan selects the smallest useful set.

## Research receipt

A completed research episode should produce a receipt with at least:

```yaml
research_id:
trigger_task_ids: []
branch_keys: []
trigger_signals: []
questions: []
queries: []
sources:
  - source_ref:
    source_class:
    title:
    published_or_updated:
    retrieved_on:
claims:
  - statement:
    source_refs: []
    confidence:
    fact_or_inference:
uncertainties: []
inspirations:
  - idea:
    source_refs: []
    analogy_boundary:
opportunities: []
no_op_reason:
authority_effect: NONE
promotion_state: CANDIDATE_ONLY
```

Receipts must preserve the distinction between quoted/source-supported facts, model inference, and design inspiration.

## Opportunity candidate

A promising idea enters `devos/opportunities.jsonl`, not the production backlog directly.

```yaml
opportunity_id:
title:
status: CANDIDATE
branch_keys: []
trigger_task_ids: []
need:
proposal:
source_refs: []
evidence_refs: []
expected_value:
novelty_reason:
project_fit:
risks: []
validation_plan: []
suggested_disposition:
authority_effect: NONE
promotion_state: CANDIDATE_ONLY
```

Suggested dispositions:

```text
NO_OP
PARK
RESEARCH_MORE
PROPOSE_TASK
PROPOSE_FEATURE_INCUBATION
PROPOSE_EXPERIMENT
PROPOSE_ARCHITECTURE_COMPARISON
```

A candidate should fail the usefulness gate if it cannot name the active RepoHarvester need it serves.

## Duplicate and current-state cross-reference

Before proposing an opportunity, the scout must compare it against:
- `devos/tasks.jsonl`;
- open/accepted RepoHarvester issues and decisions;
- current branch claims;
- prior opportunity candidates when available.

Disposition should be one of:

```text
NEW
SUPPORTS_EXISTING
OVERLAPS_EXISTING
CONTRADICTS_EXISTING
SUPERSEDED
INSUFFICIENT
```

The scout should prefer strengthening an existing task over creating a near-duplicate idea.

## Research budget

`devos/research-policy.json` defines the default query/source/opportunity budget.

The budget is a ceiling, not a target. Stop early when:
- the decisive primary evidence is found;
- additional sources are derivative duplicates;
- the project-fit test fails;
- the question is answered with sufficient confidence;
- continued browsing is unlikely to change the disposition.

## Project-fit gate

Every opportunity must answer:

1. Which active RepoHarvester milestone, task, branch need, or capability gap does this serve?
2. What becomes better if adopted?
3. What is the cheapest meaningful validation?
4. What new risk/cost does it introduce?
5. Is this a transferable principle or a context-specific trick?

If the first answer is missing, the opportunity is novelty without need and should be rejected or parked.

## Relationship to the Learning Spine

```text
ACTIVE TASK / CAPABILITY GAP / DESIGN NEED
                ↓
        RESEARCH PREFLIGHT
                ↓ when triggered
          RESEARCH-SCOUT
                ↓
     RESEARCH FINDINGS + INSPIRATION
                ↓
      CROSS-REFERENCE CURRENT STATE
                ↓
        OPPORTUNITY CANDIDATES
                ↓
   TASK | FEATURE INCUBATION | EXPERIMENT
                ↓
       NORMAL DEVOS EVALUATION PATH
                ↓
        STONE → MASON → PR → CI → CANARY
```

The scout expands the candidate space. It does not own candidate promotion.

## Auditability

High-value research must preserve:
- the trigger that caused research;
- queries or research questions used;
- source URLs/identities;
- dates/freshness where relevant;
- rejected alternatives and why;
- the distinction between fact, inference, and inspiration;
- source diversity sufficient for the claim risk;
- the candidate/no-op outcome.

This matters because a persuasive research narrative can still be wrong, stale, derivative, or optimized around a misleading benchmark.
