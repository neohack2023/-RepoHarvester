# Cross-Repository Tool Registry Contract

`devos/tools.jsonl` is RepoHarvester's local routing projection for approved reusable tools that live outside this repository.

It is routing metadata, not a vendoring mechanism, capability escalator, trust shortcut, or replacement for a tool repository's own contract.

## Required behavior

For every registered tool:

1. Resolve the exact external repository and a verified revision before use.
2. Read the tool's declared usage contract before relying on capabilities.
3. Treat each capability independently. One verified capability does not imply another.
4. Preserve explicit unsupported or narrower-language states.
5. Never upgrade `unsupported` or unverified capability claims by inference from a successful adjacent workflow.
6. Keep external source repositories read-only unless the user explicitly requests work in that repository.
7. Do not copy the external tool into RepoHarvester merely because it is registered.
8. Record demonstrated limits and evidence from real RepoHarvester usage where useful.

## Maturity

Allowed registry maturity states:

- `candidate` — known tool, not yet proven in an RepoHarvester workflow.
- `verified` — at least one bounded RepoHarvester workflow has exercised the registered capability envelope successfully.
- `deprecated` — retained for lineage but should not be selected for new work.

## Capability qualification

Allowed capability qualification states:

- `verified` — supported by the external tool's own evidence and accepted RepoHarvester routing evidence.
- `candidate` — plausible/declared but not yet proven sufficiently for RepoHarvester routing.
- `unsupported` — explicitly outside the proven capability envelope.

A capability entry must name its scope and language coverage. `languages: ["*"]` means the capability is representation/language agnostic at the stated scope, not that semantic parsing exists for every language.

## Selection law

The orchestrator should select the smallest registered capability that lawfully satisfies the task. If the requested operation exceeds the proven envelope, degrade to a narrower supported layer or stop and surface the gap. Never counterfeit a semantic layer that the tool has not proven.

## Current fixture

`repo-harvester` is self-registered from its accepted checkpoints. It is verified for repository/file provenance and deterministic TypeScript semantic extraction. C# semantic code-unit extraction remains explicitly unsupported until its open implementation slice is merged and verified.
