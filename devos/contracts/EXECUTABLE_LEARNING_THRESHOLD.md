# DevOS Executable Learning Threshold

Status: implementation slice tracked by Issue #41.

Goal: demonstrate a measurable progression from a reasoned solution to a validated procedure, then to a reusable capability that transfers to unseen work.

This slice keeps learning separate from authority. No procedural consolidator, capability graph update, or evaluation result may mutate project-wide authority directly. Any durable project mutation must continue through STONE -> MASON -> PR -> CI -> canary.

## Executable path

```text
reflection/evidence candidate
  -> procedure candidate
  -> deterministic evaluation pyramid
  -> validated procedure
  -> capability graph update
  -> held-out transfer evidence
  -> reusable capability candidate
  -> STONE/MASON boundary
```

## Required invariants

- procedures have deterministic identities derived from executable semantics and provenance;
- validation requires hard-invariant success before higher tiers count;
- training/development evidence cannot substitute for held-out transfer;
- holdout fixtures must be disjoint from training/development fixture identities;
- capability maturity may advance only from recorded evaluation evidence;
- T5 is a canary boundary, not an automatically simulated success;
- authority_effect is always NONE inside this layer;
- promotion_state remains CANDIDATE_ONLY until governed promotion.

## Initial maturity mapping

```text
RECALL                procedure exists but is not validated
RECOGNITION           T0 + T1 pass
REFLECTION            T0 + T1 + T2 pass
TRANSFER              at least one held-out T3 transfer passes
COMPOSITION           reserved for multi-skill composition evidence
ADAPTATION            reserved for post-change transfer under changed conditions
METACOGNITIVE_CONTROL reserved for explicit curriculum/strategy selection evidence
```

## Evaluation pyramid

- T0: hard invariants and deterministic regressions
- T1: training fixtures
- T2: development fixtures
- T3: held-out transfer fixtures
- T4: adversarial/counterfactual fixtures
- T5: real-work canary, represented as a required external evidence boundary

A candidate is `VALIDATED_FOR_TRANSFER` only when T0-T3 requirements pass. T4 failures do not erase the fact that transfer occurred, but they remain visible in the fitness profile and block any future policy that requires adversarial robustness.

## First proof

The regression suite must contain a procedure whose training/development fixtures cover known inputs while a distinct held-out fixture exercises the same contract on unseen input. The resulting capability must advance to TRANSFER only after that held-out fixture passes.
