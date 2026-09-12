# Agent coordination receipts

This directory stores lightweight evidence pointers produced while coordinating repository work.

A coordination receipt may record:

- task ID
- exact base and implementation revisions
- commands or checks executed
- focused test results
- reviewed files
- external source revisions
- compatibility findings
- reviewer disposition

Suggested name:

```text
RECEIPT_<task-id>_<role>_<yyyy-mm-dd>.md
```

## Boundary

These receipts are coordination evidence only.

They must not replace or weaken RepoHarvester's product evidence contracts, including provenance records, extraction receipts, qualification decisions, qualification receipts, or `CHECKPOINT.md`.

Do not place secrets, credentials, private tokens, large generated artifacts, harvested repositories, databases, or binary caches here.
