# DevOS Applied Learning Spine

Status: **Candidate / Research-backed**  
Tracks: Issue #19  
Evidence: `docs/research/RESEARCH_DELTA_0003_DEVOS_APPLIED_LEARNING.md`

This document defines the candidate shape of RepoHarvester's next DevOS learning layer. It is not an authority promotion and does not authorize autonomous self-modification.

## Operating law

> Experience may nominate a lesson. Independent evidence may strengthen it. Evaluation may demonstrate utility. Only governed promotion may make it durable operating knowledge.

## Why this exists

Current DevOS can record observable feedback and nominate repeated signatures, but repetition is not the same thing as learning. A developmental system needs to distinguish:

- observation from interpretation;
- prevalence from independence;
- reflection from truth;
- memory from authority;
- training success from transfer;
- candidate generation from promotion;
- merged code from demonstrated improvement.

## Learning Spine

```text
OBSERVE
  ↓
NORMALIZE ATOMIC FINDINGS
  ↓
CROSS-REFERENCE CURRENT STATE
  ↓
RESOLVE LINEAGE + COLLAPSE DERIVATIVES
  ↓
TRIANGULATE INDEPENDENT ROOTS
  ↓
REFLECT / DIAGNOSE
  ↓
CONSOLIDATE EXPERIENCE
  ↓
UPDATE CAPABILITY GRAPH
  ↓
SELECT CURRICULUM TARGET
  ↓
GENERATE CANDIDATES
  ↓
EVALUATE FOR TRANSFER + REGRESSION
  ↓
STONE
  ↓
MASON
  ↓
PR + CI + CANARY
  ↓
POST-CHANGE RE-TRIANGULATION
  ↓
PROMOTE | REVISE | ROLLBACK | NO-OP
```

## Required local objects

### Atomic finding

```yaml
finding_id:
episode_id:
branch_key:
statement:
finding_type:
source_ref:
root_ids: []
created_at:
```

Finding types should remain narrow and machine-queryable, for example:

```text
OBSERVATION
FAILURE
SUCCESS
CONSTRAINT
WORKFLOW_FACT
RESEARCH_FINDING
USER_DECISION
```

### Cross-reference

```yaml
cross_reference_id:
finding_id:
compared_claim_ids: []
disposition:
match_evidence: []
```

Disposition:

```text
NEW
SUPPORTS
CONTRADICTS
SUPERSEDES
PARTIAL_OVERLAP
INSUFFICIENT
```

This stage compares semantics against current local state. It does not change authority.

### Evidence root / lineage
Use Research Delta 0002 as the owning design for roots, lineage edges, derivative collapse, reproduction, replication, partial shared inputs, and unknown lineage.

### Triangulation batch

```yaml
triangulation_batch_id:
concept_key:
finding_ids: []
root_ids: []
independent_root_count:
correlated_root_count:
reproduction_count:
unknown_lineage_count:
signal:
divergence_refs: []
```

Signal:

```text
CONVERGENCE
DIVERGENCE
SINGLETON
ORTHOGONAL
INSUFFICIENT
```

Root count never changes authority by itself.

### Reflection candidate

```yaml
reflection_id:
episode_ids: []
observed_failure:
expected_behavior:
mechanism_hypothesis:
evidence_for: []
evidence_against: []
alternative_explanations: []
proposed_lesson:
proposed_scope:
required_disconfirmation_test:
```

A reflection is a hypothesis-bearing artifact.

### Memory representations

```text
EPISODIC   = what happened in a specific execution
SEMANTIC   = a lesson supported across evidence
PROCEDURAL = an executable/retrievable skill
NEGATIVE   = a known failure mode or rejected strategy
```

Evidence roots and immutable source refs remain underneath every evolved representation.

### Capability

```yaml
capability_id:
branch_scope:
description:
prerequisites: []
known_tasks: []
known_failure_modes: []
maturity_stage:
recent_eval_profile:
transfer_profile:
abstention_profile:
```

Maturity stages:

```text
RECALL
RECOGNITION
REFLECTION
TRANSFER
COMPOSITION
ADAPTATION
METACOGNITIVE_CONTROL
```

These are engineering maturity levels only.

### Procedural skill

```yaml
skill_id:
version:
branch_scope:
trigger_conditions:
inputs:
outputs:
implementation_ref:
preconditions:
known_failures:
training_fixture_ids: []
development_fixture_ids: []
holdout_fixture_ids: []
transfer_evidence_ids: []
fitness_profile:
rollback_ref:
```

## Curriculum

Curriculum exists to improve current product-development capabilities, not to maximize novelty.

Inputs:

```text
current product frontier
open capability gaps
failure recurrence
triangulation strength
transfer potential
cost/risk budget
```

Curriculum outputs a bounded practice or experiment, not a self-authorized change.

Examples:

- prove the engine-comparison retrieval packet works on an unseen runtime question;
- improve cross-reference handling of stale vs superseded repository docs;
- practice generating regression fixtures from a Magic fuzz failure;
- reduce repeated context over-expansion in one feature branch.

## Candidate generation

DevOS should support multiple proposers behind one stable contract.

```text
REFLECTIVE_MUTATOR
EVOLUTIONARY_PROGRAM_MUTATOR
RULE_REPAIR
AGENT_DESIGN_PROPOSAL
HUMAN_DESIGN_PROPOSAL
```

Do not couple promotion logic to one optimizer.

## Evaluation pyramid

```text
T0 hard invariants / deterministic regressions
T1 training fixtures
T2 development fixtures
T3 held-out transfer
T4 adversarial / counterfactual
T5 canary real work
```

Rules:

1. The same evidence that generated a candidate cannot be the only promotion evidence.
2. Evaluators are versioned separately from candidates.
3. Holdouts cannot expose unavailable answers/implementation history.
4. Trace inspection is required for high-value optimizations to detect shortcut behavior.
5. Riskier changes require stronger transfer and canary evidence.

## Fitness profile

Do not use one universal score.

Track:

```text
correctness
held_out_transfer
regression_rate
abstention_calibration
scope_integrity
provenance_integrity
authority_integrity
determinism
context_tokens
latency
cost
review_burden
```

Hard governance failures dominate any performance gain.

## Governance boundary

Learning objects are not authority objects.

```text
learning candidate
→ evaluation evidence
→ STONE package
→ MASON classification/write plan
→ authorized repo mutation
```

No optimizer, curriculum process, reflection, memory consolidator, or capability registry may mutate project-wide authority directly.

## Product alignment rule

DevOS exists to shorten RepoHarvester's development loop.

Every learning experiment should answer at least one:

- Which active product milestone does this accelerate?
- Which repeated development failure does this remove?
- Which capability does this make transferable across branches?
- Which context/evidence cost does this reduce?
- Which risk does this catch earlier?

If none apply, the experiment is not a DevOS priority.

## First executable slices

1. **Cross-reference core** — deterministic fixtures for `NEW/SUPPORTS/CONTRADICTS/SUPERSEDES/PARTIAL_OVERLAP/INSUFFICIENT`.
2. **Lineage + triangulation** — implement Issue #17 root collapse and independent-root signals.
3. **Reflection + memory** — structured reflection and episodic/semantic/negative stores.
4. **Capability + skill registry** — track maturity and transfer evidence.
5. **Evaluation pyramid** — train/dev/holdout/adversarial partitions and multi-objective results.
6. **Curriculum** — choose bounded learning work from the active product frontier.
7. **Shadow optimizer** — generate candidates without promotion authority.
8. **Governed improvement** — STONE/MASON → PR → canary → causal closure.

Do not start with open-ended code self-modification. Earn that capability through the preceding gates.
