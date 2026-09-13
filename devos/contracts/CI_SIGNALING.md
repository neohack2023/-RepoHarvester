# DevOS CI Signaling Contract

RepoHarvester CI should be quiet when healthy and concrete when unhealthy.

## Operating law

**Green CI whispers. Red CI identifies the failed gate, preserves the evidence, and gives the exact reproduction command.**

CI is an observation surface, not a diagnosis oracle and not an authority source.

## Healthy-run behavior

A passing gate should emit only a compact status line. Full command output may be captured to a local runner file for symmetry, but it should not flood ordinary workflow logs or create durable artifacts.

Verbose runner and step debugging remain opt-in for troubleshooting rather than permanent background noise.

## Failure behavior

A failed gate must emit all of the following:

1. one GitHub Actions error annotation naming the gate;
2. the exact local reproduction command;
3. the process exit code;
4. a stable failure signature derived from the gate, command, and normalized failure signal;
5. the inspectable normalized failure signal plus its normalization-version identifier;
6. a concise output excerpt sufficient to orient debugging;
7. the path to the complete captured log;
8. run metadata sufficient to identify the CI observation root;
9. explicit CI subject identity;
10. a machine-readable `repoharvester-ci-failure/v1` packet with `authority_effect: NONE`.

The workflow should upload `.build/ci/` only when a job fails.

## CI subject identity

Do not collapse the source change and the revision actually tested into one field.

For a normal `pull_request` workflow, GitHub tests the synthetic pull-request merge ref by default. Therefore:

- `tested_sha` is the commit actually exercised by the workflow, normally `GITHUB_SHA`;
- `change_head_sha` is the pull request head commit from the event payload;
- `base_sha` is the pull request base commit from the event payload;
- `kind` records whether the subject is a normal commit, pull-request merge simulation, or another supported event shape;
- `identity_state` is `COMPLETE` only when the revision identities required for that event are known.

A green pull-request run is evidence about the tested merge subject associated with that change head. It must not be rewritten as evidence that the PR head was tested in isolation.

If a pull-request event payload cannot provide the change-head SHA, the packet must preserve `change_head_sha: null` with `identity_state: INCOMPLETE`. It must never substitute the synthetic merge SHA as a fake source-head identity. Downstream reflection fails closed on incomplete subject identity.

For ordinary push runs, `tested_sha` and `change_head_sha` may be the same commit.

## Evidence posture

One workflow run is one observation-generating root for that gate. A rerun of the same revision and inputs is reproduction evidence, not automatically a new independent root. Summaries, annotations, uploaded logs, failure packets, and later agent reports derived from that run remain descendants of the same root.

The normalized failure signal is observable evidence used for stable signatures and later reflection input. It is not a root-cause claim.

CI failure packets may later feed the Learning Spine, STONE, or MASON. They do not themselves create lessons, issues, governance changes, or promotion.

## Noise controls

- cancel superseded pull-request runs through workflow concurrency;
- keep repository permissions read-only unless a workflow explicitly requires more;
- prefer bounded timeouts over indefinitely hanging jobs;
- stop normal gate execution on the first real failure to avoid cascade noise;
- retain full failure artifacts for a short debugging window rather than indefinitely;
- do not automatically open GitHub issues for every failure;
- do not automatically retry deterministic failures until they pass.

## Diagnostic escalation

When the default failure packet is insufficient, rerun with GitHub Actions step or runner debug logging enabled. Permanent verbose logging is not the first-line debugging strategy.

## Security and privacy

Failure excerpts and artifacts must not intentionally echo secrets or hidden reasoning. GitHub documents automatic redaction for workflow logs, but a captured file is still an artifact payload and must be treated as potentially sensitive until reviewed by the producing gate.

Therefore:

- keep CI commands bounded and avoid intentionally printing credentials or complete sensitive contexts;
- register derived sensitive values for masking before they can reach logs;
- do not assume a raw captured file is safe merely because console output would be masked;
- keep short artifact retention and read-only workflow permissions as defense in depth;
- if a future gate legitimately handles secrets, define a gate-specific artifact policy before uploading its raw output.

## Local entry point

Each workflow gate is wrapped through:

```bash
python tools/ci_goblin.py --gate "<gate name>" -- <command...>
```

Success returns the wrapped command's success status with compact output. Failure preserves the log, summary, annotation, subject identity, and evidence packet before returning a failing status to GitHub Actions.
