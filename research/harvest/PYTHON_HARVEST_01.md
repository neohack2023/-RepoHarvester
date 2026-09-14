# PYTHON_HARVEST_01

## Status

CHECKPOINT REACHED as a validated implementation candidate. Promotion to `main` remains gated on repository-wide PR validation.

## Source and implementation binding

- RepoHarvester base before this slice: `4fe357303098aa669deb8aed6144580c9d7abb34`
- validated implementation candidate: `eb78d102e9a36ee4a78a3fb16aa7451c08128ce6`
- external target: `https://github.com/kdbhalala/agi-memory.git`
- exact target revision: `3c93e9e52b4038578501e2bbe4c374476d6db34f`
- source repository was not modified by harvesting

## Bounded capability added

RepoHarvester can now decompose Python source into deterministic provenance-backed code units using the Python standard-library AST.

Implemented Python unit kinds:

- top-level and nested functions
- classes
- class methods
- module-level SCREAMING_SNAKE constants

Each unit retains the existing `HarvestRecord` provenance contract:

- repository and exact revision
- source path
- unit kind and deterministic identity
- language
- source-file SHA-256
- representation SHA-256
- exact source representation
- byte and row/column spans
- deterministic path/symbol tags
- lifecycle state

Python structural evidence also adds:

- file -> code-unit `contains` relationships
- Python `imports` relationships
- repository-local import targets resolved conservatively as `EXACT`
- non-local absolute imports preserved as `EXTERNAL`
- unresolved relative targets remain explicit rather than fabricated

Empty source files are normalized from their source SHA-256 rather than trusting ingestion display text.

## Validation

GitHub Actions acceptance run: `34868649174`

Focused tests:

- Python symbol extraction
- Python parse-error fail-closed behavior
- Python containment/import relationships
- Python SQLite corpus round trip
- existing generic corpus regression suite

Result: `8 passed`.

The acceptance workflow then executed RepoHarvester's existing `scripts/run_corpus_harvest.py` against the pinned external repository and reopened the resulting database through `SQLiteHarvestStore`.

## Corpus result

Database: `acceptance/corpus/harvest.sqlite3`

- total records: `652`
- file records: `88`
- repository-license evidence records: `1`
- Python symbol records: `563`
  - classes: `28`
  - constants: `108`
  - functions: `239`
  - methods: `188`
- relationships: `1028`
  - contains: `563`
  - imports: `465`
- relationship resolution states:
  - EXACT: `722`
  - EXTERNAL: `306`
- semantic skips: `0`
- warnings: `0`
- qualification state: all `RAW`
- source worktree clean after harvest: `true`
- extraction receipt reproduction: `true`

Receipt manifest SHA-256:

`5320068e7bf2e22cdca34ca1793c208771ef64b6380704322f5c4ca44c9f0b79`

Relationship manifest SHA-256:

`b42e62ffb0da8a7f2ba2c1acc92505a8b4bdcedf86396bce0c806463c61bd59e`

## Evidence artifact

- artifact: `agi-memory-repoharvester-corpus`
- artifact ID: `10358336468`
- artifact digest: `sha256:162d11be7fd3a43ad99abe26df3d67211bdc46b6998d6d1027f603b79a8c6ace`
- artifact contents:
  - `harvest.sqlite3`
  - `EXTRACTION_RECEIPT.json`
  - `HARVEST_SUMMARY.json`
  - `DB_INSPECTION.json`

## Qualification disposition

This checkpoint proves deterministic extraction and persistence only. All external material remains `RAW`.

No `agi-memory` code or architectural pattern is automatically trusted, copied into RepoHarvester, or promoted to `CANDIDATE`, `TAGGED`, `VERIFIED`, or `REUSABLE` by this slice.

## Known boundary exposed by this target

RepoHarvester's declared-dependency evidence currently handles root `package.json` only. `agi-memory` uses `pyproject.toml` and declares an empty Python dependency list. Therefore Python dependency evidence remains a separate future slice; this harvest does not fabricate a dependency record merely to satisfy qualification.

## Next gate

After repository-wide validation and main promotion of Python extraction, the smallest useful follow-up is `PYPROJECT_DEPENDENCY_EVIDENCE_01` if qualification of Python code units is required. Otherwise, keep the stored `agi-memory` corpus RAW and use it for evidence-backed comparison/retrieval only.
