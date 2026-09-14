# FORK_SAFE_DEPENDENCY_AUDIT_01

## Status

COMPLETE candidate, pending final exact-head promotion to `main`.

## Root cause

RepoHarvester intentionally remains a GitHub fork of `coderamp-labs/gitingest`. GitHub's dependency-review API returns `403` when used against forks, so the inherited `actions/dependency-review-action` workflow cannot produce dependency-diff evidence for this repository class.

This is a host capability mismatch, not evidence of a vulnerable dependency.

## Replacement contract

The replacement workflow:

1. preserves the repository's fork relationship;
2. records `github_dependency_review = UNSUPPORTED_FORK` rather than treating platform unavailability as a project regression;
3. installs RepoHarvester's `[dev,server]` dependency set on Python 3.13;
4. captures the concrete resolved environment in `dependency-resolution.txt`;
5. audits that resolution with pinned `pip-audit==2.10.1`;
6. emits machine-readable `dependency-audit.json` plus `dependency-audit-context.json`;
7. binds evidence to both the exact candidate SHA and GitHub's merge-test SHA;
8. uploads the evidence as an immutable GitHub Actions artifact;
9. fails only when the independent audit reports a vulnerability or cannot complete.

## Validation evidence

Validated candidate before checkpoint sealing:

- candidate SHA: `ae79ffc2fb6ad112b3a7ac71b303332e107c1100`
- base SHA: `214b3b9b9fc2af4d03bf7265baac3cb55b845fbc`
- merge-test SHA: `8d3177aeebb53772e6b3ea21d256bd3db350d6d3`
- Dependency Audit run: `34795205445`
- Dependency Audit job: `103826822960`
- audit tool: `pip-audit==2.10.1`
- resolved dependencies audited: `82`
- known vulnerabilities returned: `0`
- audit exit code: `0`
- evidence artifact ID: `10328983689`
- artifact digest: `sha256:8562ec292d1d65843db444bb144d241d8d1e3f3586fa287211a52d5e1bcf51bb`
- artifact name: `dependency-audit-ae79ffc2fb6ad112b3a7ac71b303332e107c1100`

Companion gates on the same candidate also passed:

- DevOS checks: `34795205415`
- DevOS Live Adoption: `34795205346`
- External Acceptance: `34795205369`
- Corpus Harvest Smoke: `34795205353`
- PR Conventional Commit Validation: `34795205335`

## Authority

This checkpoint records accepted evidence but does not itself authorize durable promotion. The checkpoint-sealing commit must pass the replacement dependency audit and RepoHarvester validation gates again before PR #25 may merge.

Branch protection remains intentionally optional for this consumer repository per owner policy. Exact-head validation remains the promotion gate.
