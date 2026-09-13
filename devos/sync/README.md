# Governance Sync

This directory stores public/repository-safe immutable receipts for bounded upstream RepoHarvester governance synchronization.

Normal repository agents should not fetch Notion for orientation. Read `../governance-lock.json` and `../contracts/UPSTREAM_SYNC.md` first.

Receipts prove what upstream objects were compared, the bounded delta classification, the repository base identity, and the resulting freshness window. They never imply authority cutover.
