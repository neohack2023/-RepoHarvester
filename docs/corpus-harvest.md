# Dynamic corpus harvesting

`run_corpus_harvest.py` is the generic repository intake path. It is deliberately separate from `run_external_acceptance.py`, which remains the pinned PCM product acceptance gate.

The corpus runner accepts a Git repository URL, resolves an exact revision, harvests the deterministic evidence RepoHarvester currently supports, and upserts that evidence into a shared SQLite database without deleting evidence from previously harvested repositories.

## Usage

Harvest remote HEAD and pin the resolved commit automatically:

```bash
python scripts/run_corpus_harvest.py \
  https://github.com/nradawg/backoff-schedule \
  --database .repoharvester/corpus.sqlite3 \
  --output-dir .repoharvester/runs/backoff-schedule
```

Harvest an explicitly requested commit or remote ref:

```bash
python scripts/run_corpus_harvest.py \
  https://github.com/nradawg/backoff-schedule \
  --revision f4ed89aca0618c169ed68ccb2a261df8b971f415 \
  --database .repoharvester/corpus.sqlite3 \
  --output-dir .repoharvester/runs/backoff-schedule
```

Each run writes `EXTRACTION_RECEIPT.json` and `HARVEST_SUMMARY.json`. The SQLite file is shared and cumulative. Reharvesting the same repository/revision is idempotent under the existing record and relationship identities.

## Current extractor coverage

Every supported repository still receives file-level provenance records. RepoHarvester currently adds semantic symbol and relationship evidence for TypeScript, root repository-license evidence where supported, and root `package.json` declared-dependency evidence where present.

Unsupported languages do not receive invented semantic code units. They remain file-level evidence until a deterministic extractor exists.

## Lifecycle boundary

Generic corpus harvesting is qualification-neutral:

```text
repository -> exact revision -> RAW records -> SQLite corpus -> extraction receipt
```

The runner does not perform `RAW -> CANDIDATE`, tagging, verification, or reusable-code promotion. Those lifecycle transitions remain separate gates with their own evidence requirements.

The PCM external acceptance workflow remains a fixed fixture for proving known product behavior. It is not the generic corpus-harvest interface.
