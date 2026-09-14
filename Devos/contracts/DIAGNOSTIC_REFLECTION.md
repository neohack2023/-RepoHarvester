# DevOS Diagnostic Reflection Contract

Structured reflection is the first hypothesis-bearing stage above observable CI evidence. It is not automatic diagnosis and it is not mutation authority.

## Operating law

**A failure may justify a hypothesis. A hypothesis must name alternatives and a disconfirmation test. Only later evidence may localize a cause.**

## Input boundary

A reflection candidate consumes:

- one `repoharvester-ci-failure/v1` packet;
- one explicit reflection request;
- optional expected tested/change-head SHAs supplied by the caller.

The source packet must be failed, authority-neutral, use a recognized signal-normalization version, contain an inspectable normalized signal, and carry complete subject identity for both the tested revision and the source change revision.

## Required reflection fields

Every reflection request must provide:

- branch key;
- failure domain;
- references to evidence supporting that domain classification;
- expected behavior;
- mechanism hypothesis;
- evidence for and/or against the hypothesis when available;
- at least one alternative explanation;
- predicted consequence if the hypothesis is correct;
- a required disconfirmation test;
- proposed scope.

A plausible explanation without a competing explanation and falsification path is commentary, not a DevOS reflection candidate.

## Classification boundary

Failure-domain classification is itself evidence-bound. An agent may not use a convenient label to bypass the correct diagnostic path.

Current domains:

- `CODE`
- `TEST`
- `RUNTIME`
- `ENVIRONMENT`
- `RETRIEVAL`
- `TOOL_CONTRACT`
- `INSTRUCTION`
- `UNKNOWN`

Routing is deterministic after the classification is supplied:

- code, test, runtime, environment, retrieval, and tool-contract claims receive `COMPONENT_DEBUG_REQUIRED` and route to the existing harness/component-debug path;
- instruction-level hypotheses receive `INTERVENTION_REQUIRED` and route to the existing Failure Intervention Attribution gate before any localized instruction candidate exists;
- unknown failures remain `NEEDS_CLASSIFICATION`.

The routing disposition is a next-step control, not proof that the supplied classification is correct. Classification evidence remains inspectable and may be contradicted by later observations.

## Subject and signal binding

The candidate carries forward:

- source packet digest;
- source failure signature;
- observation root;
- signal-normalization version;
- source subject kind;
- tested SHA;
- change-head SHA;
- base SHA when available.

Incomplete subject identity is not eligible for reflection. When a caller supplies expected SHAs, mismatch fails closed.

## Output boundary

`repoharvester-reflection-candidate/v1` is always:

- `authority_effect: NONE`;
- `promotion_state: CANDIDATE_ONLY`.

A reflection candidate cannot directly change code, prompts, tools, routing, memory authority, or project canon.

## Promotion boundary

A reflection may become input to bounded debugging, intervention attribution, further evidence gathering, or later STONE intake. It may not skip:

- causal localization where required;
- held-out/regression evidence appropriate to the change;
- STONE source/evidence bounding;
- MASON classification and destination control;
- normal repository review and CI.

## Deferred deliberately

This first slice does not persist reflections into SQLite, consolidate them into semantic/procedural memory, update capability maturity, choose curriculum, or generate optimizer mutations. Those stages require real reflection episodes and transfer evidence first.
