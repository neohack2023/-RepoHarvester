# Code-unit extraction agent contract

This feature owns deterministic extraction of symbol/code-unit records from already ingested source files while preserving exact provenance.

## Required behavior

- Re-check GitHub `main`, root `AGENTS.md`, and `CHECKPOINT.md` before starting work.
- Keep file-level evidence intact. Code-unit records extend file evidence; they do not replace it.
- Preserve exact source repository, revision, path, language, source hash, representation hash, RAW lifecycle state, and extractor identity.
- Give every extracted unit an exact source range and stable deterministic identity.
- Extraction must be deterministic and parser-backed. Do not use an LLM to decide source boundaries or symbol locations.
- Malformed or partially parseable files must fail explicitly or emit bounded parser evidence; never fabricate missing symbols.
- Nested declarations and duplicate names must remain distinguishable.
- Add adversarial fixtures for duplicate names, nesting, anonymous constructs where applicable, syntax errors, line-ending variation, and malformed files.
- Preserve Python/upstream compatibility unless the slice explicitly evaluates and approves a compatibility change.
- Keep extraction separate from semantic interpretation, architectural classification, qualification, similarity scoring, and reusable-code promotion.

## First slice boundary

`CODE_UNIT_EXTRACTION_01` supports exactly one language and one parser/extractor path.

The first slice should implement only what is needed to prove:

repository/revision -> file record -> deterministic code units -> SQLite persistence/query -> receipt/reproduction evidence

Do not add cross-repository similarity, vectors, LLM classification, dependency graphs, or license qualification in this slice.

## Parser qualification

Before adopting a parser/runtime dependency, record:

- supported language/version
- runtime requirements
- impact on the inherited gitingest compatibility floor
- deterministic source-range behavior
- behavior on incomplete/invalid syntax
- maintenance/license status
- extractor version that can be included in receipts

Tree-sitter is the preferred architectural candidate from research, but the current TypeScript Python grammar package may raise the Python floor above inherited gitingest support. Do not silently make that tradeoff.

## Evidence gate

A slice is not complete until focused tests prove stable identities and source ranges, SQLite round-trip/query behavior is preserved, receipt reproduction detects evidence drift, and a pinned real repository or accepted fixture completes the path without source mutation.

Checkpoint only after those gates pass.
