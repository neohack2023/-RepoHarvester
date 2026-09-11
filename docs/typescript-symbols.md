# TypeScript symbol extraction v1

RepoHarvester's first code-unit extractor is deterministic and TypeScript-only.

## Scope

`typescript-symbol-v1` extracts named TypeScript/TSX code units from an existing file-level `HarvestRecord` using Tree-sitter. It does not interpret quality, architectural role, intent, or reuse suitability.

Supported first-slice units include named functions, classes, interfaces, type aliases, enums, methods/signatures, and variables whose initializer is a function/arrow function.

## Provenance contract

Every symbol record carries forward:

- exact source repository
- exact source revision
- unchanged source file path
- whole-file `source_sha256`
- symbol-only `representation_sha256`
- deterministic `unit_identity`
- qualified `symbol_name`
- zero-based byte start / exclusive byte end
- 1-based line and column start/end
- deterministic tags
- `RAW` qualification state

`unit_identity` has the form:

`<symbol-kind>:<qualified-name>@<start-byte>:<end-byte>`

Locations are stable for the exact source revision. They are not intended to remain stable across source edits; cross-revision lineage is a later qualification problem.

## Storage

SQLite schema version 2 adds a separate `unit_identity` so multiple symbols from one file can be stored without changing the true file path. Schema version 1 databases migrate in place with existing file records retaining an empty `unit_identity`.

## Receipt behavior

Extraction receipt v2 binds symbol identity and source-location fields into the manifest hash. Receipt v1 verification remains supported so existing Checkpoint 1 evidence can still be reproduced with its original manifest shape.

## Boundary

Symbol discovery is not qualification. Extracted units remain `RAW`. This slice adds no LLM classification, vector search, semantic ranking, reuse promotion, or automatic code copying.
