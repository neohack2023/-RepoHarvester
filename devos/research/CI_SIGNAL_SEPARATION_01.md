# CI_SIGNAL_SEPARATION_01

## Problem

RepoHarvester's broad pull-request matrix mixed three different evidence classes:

1. deterministic core behavior;
2. shared-corpus persistence/integrity behavior;
3. live probes against external Git providers.

The live provider probes depend on third-party availability, authentication policy, HTTP behavior, and rate limits. Their failures therefore cannot be interpreted as deterministic RepoHarvester regressions.

The corpus failure observed during FORK_SAFE_DEPENDENCY_AUDIT_01 was separate. `harvest_into_corpus()` deliberately emits file, symbol, license, and declared-dependency records, while `SQLiteHarvestStore.query_records()` deliberately returns records in deterministic provenance/path/unit order. The old test incorrectly required harvest construction order to equal storage query order.

## Decision

- `live_network` tests are excluded from pull-request core CI.
- External Git provider probes run only in `Provider Live Smoke`, on a weekly schedule or explicit manual dispatch.
- `corpus_integrity` tests run in a dedicated deterministic pull-request job named `corpus integrity`.
- Core CI continues to run across the existing OS/Python matrix but excludes both specialized markers.
- The corpus round-trip assertion compares the returned SQLite order against the harvested records sorted by the storage identity order rather than assuming construction order is a persistence contract.

## Evidence interpretation

A failure in `core (...)` means a deterministic general regression on that platform/runtime.

A failure in `corpus integrity` means a deterministic persistence/round-trip contract regression.

A failure in `Provider Live Smoke` means a live provider compatibility or availability observation. It is actionable evidence, but it is not a pull-request authority failure by itself.

## Authority

This document records the intended evidence semantics. Promotion still requires the exact candidate head to pass deterministic RepoHarvester/DevOS gates. Branch protection remains optional for this consumer repository per owner policy.
