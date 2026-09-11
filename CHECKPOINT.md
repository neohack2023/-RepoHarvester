# First external repository acceptance checkpoint

- Date: 2026-09-11
- Repository: neohack2023/-RepoHarvester
- Verified main/base before acceptance: ad4525d62064610f76b3ba2cfb6408f32284f052.
- Acceptance target: `anthonylee991/pcm` at exact revision
  `5dfb7ecca889dd8c12b8d088a1cbf91e4f8d1cf8`.
- Checkpoint head: the commit containing this file (resolve with Git; avoids self-referential SHA).
- Maturity: the first bounded end-to-end external repository path is proven: exact Git provenance -> structured RAW
  file records -> deterministic baseline tags -> local SQLite persistence -> exact provenance query/reload ->
  deterministic extraction receipt -> reproduction verification, without modifying the harvested repository.
- Completed foundation: versioned SQLite schema; idempotent upsert by repository/revision/path/unit kind; lossless
  record reconstruction; exact AND-filtered provenance/field/tag queries; deterministic result ordering; canonical
  receipt manifest hashing; receipt JSON round-trip; verification against SQLite-loaded records; bounded storage
  feature contract under `features/storage/`.
- Acceptance evidence: GitHub Actions `External Acceptance` passed on Python 3.12. PCM traversal produced 44 files
  across 12 directories and 305294 source bytes. SQLite stored and exactly reloaded 44/44 records. All records
  remained `RAW`; receipt verification passed; the external worktree remained clean.
- Deterministic classifications observed: 21 TypeScript, 3 Python, 13 Markdown, 3 JSON, 4 Unknown. Role tags:
  22 source, 14 docs, 3 config, 2 test, 3 unknown. Tag ruleset: `path-baseline-v1`.
- Evidence binding: receipt manifest SHA-256
  `644fb514b3dafc6c19f0260d5556ece2c7bb8dbb14aececad12598fa0f438cf7`.
  CI artifact `pcm-checkpoint-1-evidence` contains `harvest.sqlite3`, `EXTRACTION_RECEIPT.json`, and
  `ACCEPTANCE_SUMMARY.json`.
- CI note: the repository's Dependency Review job reports that dependency review is not supported because the
  repository security-analysis configuration does not provide the required dependency graph capability. This is a
  repository configuration limitation, not an acceptance-harness failure and not a harvested-source defect.
- Qualification: CHECKPOINT 1 REACHED. This proves deterministic external harvesting and evidence reproduction only.
  PCM records remain `RAW`; no external code, claim, or architectural pattern is promoted to trusted reusable knowledge.
- Known risks: schema migration beyond SQLite schema version 1 is not implemented; the receipt loader assumes trusted
  JSON shape; lexical path tags can misclassify semantic roles; harvesting remains file-level rather than symbol/code-unit
  level; license metadata is not yet attached to each harvest record.
- Next bounded action: add deterministic symbol/code-unit extraction for one supported language while preserving file
  provenance, hashes, RAW lifecycle state, and exact source-location identity. Do not add semantic ranking, vectors,
  distributed infrastructure, or automatic qualification in this slice.
- Resume: re-check GitHub `main`, exact head, and checkpoint evidence before further implementation.
