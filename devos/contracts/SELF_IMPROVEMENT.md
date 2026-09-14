# DevOS Self-Improvement Contract

RepoHarvester's development operating system may learn from its own observable failures, but it may not silently rewrite itself.

The goal is AIOS-style repository learning without authority laundering.

## Loop

```text
observable repository event
        ↓
system_feedback table
        ↓
recurrence / strong mechanical evidence
        ↓
STONE bounded candidate
        ↓
MASON authority + destination classification
        ↓
focused PR + regression/validator
        ↓
repository-accepted operating knowledge
        ↓
optional bounded upstream memory sync
```

## Runtime feedback

Record only observable facts such as:

- retrieval failure;
- utilization failure;
- stale-projection friction;
- scope leakage;
- authority conflict;
- validator gap;
- test gap;
- workflow friction.

Use:

```bash
python tools/knowledge_runtime.py feedback \
  --episode <stable-episode-id> \
  --branch <branch-key> \
  --category <category> \
  --signature <stable-mechanism-key> \
  --summary "<observable event>" \
  --evidence-ref <immutable-or-stable-evidence> \
  --severity medium
```

Do not store hidden chain-of-thought, private scratchpads, or generic dissatisfaction as system feedback.

Runtime feedback lives in `.build/repoharvester-knowledge.db` and survives ordinary knowledge rebuilds. `python tools/build_knowledge_db.py --fresh` intentionally resets it.

## Candidate threshold

A feedback event is not a rule.

The local `improvement_candidates` view nominates a pattern only after the same signature appears in at least two independent episode IDs.

A single event may still be promoted for review when:
- the owner directly locks a rule;
- a task-native verifier proves a structural invariant violation;
- the failure is severe enough that recurrence would be unsafe or destructive.

Those cases still require STONE/MASON classification and normal change review.

## Promotion law

Before accepting an improvement:

1. confirm the failure actually occurred;
2. bind immutable/stable evidence;
3. separate mechanism from symptom;
4. search for duplicate or superseded local rules;
5. state the proposed scope;
6. prove the rule does not widen unrelated authority;
7. add a regression/validator where mechanically possible;
8. review through a focused GitHub change;
9. run applicable CI;
10. decide whether an upstream Notion memory delta is material.

Repetition increases prevalence. It never upgrades authority by itself.

## Negative knowledge

Failures that are useful but too specific for general policy should remain detailed negative knowledge or feedback history rather than becoming a globally loaded rule.

## Stop conditions

Stop promotion when:
- source evidence is speculative;
- the failure cannot be reproduced or independently verified;
- the proposed rule overfits one incident;
- scope is unclear;
- the change would create a new authority source;
- the proposal depends on upstream state missing from the local bundle and an upstream sync trigger is active.

## Self-modification boundary

DevOS may propose and implement reviewed repository changes through the normal branch/PR/test path. It may not directly modify governance law merely because its own feedback table contains a frequent pattern.

The feedback database is an observation surface, not an authorization surface.
