# Deterministic baseline tags checkpoint

- Date: 2026-09-11
- Repository: neohack2023/-RepoHarvester
- Verified main/base: 3045b6952f75ecaf36cc8069bb9cb12d1c67028a
- Implementation head: 0f4569a4d7805203a93f67824a5119d6ea883a53
- Checkpoint head: the commit containing this file (resolve with Git; avoids self-referential SHA).
- Maturity: provenance-backed file records plus deterministic, versioned baseline tags.
- Completed: language, literal directory components, exclusive docs/test/config/source/unknown roles;
  immutable sorted tags stored on records, explicit path-baseline-v1 rules, backward-compatible defaults.
- Evidence: Python 3.12; `python -m pytest tests/repoharvester -q`: 29 passed.
  Covers precedence, unknowns, separators, invalid paths, repeated extraction, RAW preservation,
  hashes/provenance, source-byte preservation, and existing gitingest flattened-output contract.
  `python -m compileall -q src/repoharvester tests/repoharvester` and `git diff --check` passed.
- Warnings: pathspec emitted 450 GitWildMatchPattern deprecation warnings; tests passed.
- Blockers: none for this bounded slice. Full upstream suite was not run.
- Risks: lexical path conventions can misclassify semantic roles; suffix language is not verified.
  Existing HEAD provenance does not establish a clean worktree; this pre-existing limitation is unchanged.
- Qualification: records remain RAW. Tagging is not validation or promotion.
- Next bounded action: SQLite persistence and exact tag/provenance queries over these records.
  No SQLite, LLM interpretation, source copying, or qualification automation added here.
- Resume: re-check GitHub branch/main and review status before further implementation.
