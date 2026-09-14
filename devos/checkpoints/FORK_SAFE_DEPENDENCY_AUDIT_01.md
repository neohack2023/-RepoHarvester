# FORK_SAFE_DEPENDENCY_AUDIT_01

## Status

Candidate implementation for RepoHarvester's fork-safe dependency audit.

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
7. uploads the evidence as an immutable GitHub Actions artifact;
8. fails only when the independent audit reports a vulnerability or cannot complete.

## Authority

This checkpoint does not declare the slice complete until the exact candidate SHA passes the replacement audit and the existing RepoHarvester validation gates. Promotion remains bounded by exact-head validation. Branch protection remains intentionally optional for this consumer repository per owner policy.
