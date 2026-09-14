# Fork Dependency Review Root Cause

RepoHarvester is intentionally maintained as a GitHub fork of `coderamp-labs/gitingest`.

GitHub's dependency review REST endpoint documents HTTP 403 when used against a fork. The inherited `actions/dependency-review-action` therefore cannot provide dependency-diff evidence for this repository class, even though RepoHarvester is public and owner-controlled.

Observed failure from PR #24 / workflow run 34794412336:

`Dependency review is not supported on this repository.`

DevOS classification: `UNSUPPORTED_HOST_CAPABILITY`, not `DEPENDENCY_VULNERABILITY`.

Replacement decision: preserve fork lineage and independently audit RepoHarvester's resolved Python dependency set in CI. The replacement must emit machine-readable evidence and fail only on real audit findings or audit execution failure.

Primary external evidence: GitHub dependency review API documentation states status 403 is returned when the dependency-diff endpoint is used against a fork. PyPA documents `pip-audit` as an environment/requirements vulnerability auditor with JSON output support.
