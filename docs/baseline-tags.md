# Deterministic baseline tags

Capability disposition: EXTENSION_CANDIDATE of existing file harvest records.

`build_file_harvest_records` now attaches a sorted, unique, immutable tuple of
namespaced tags and `tag_ruleset="path-baseline-v1"`. Existing manually constructed
records default to empty tags and no ruleset. Tags are derived metadata; source
bytes, representations, hashes, revisions, and qualification states are unchanged.
Automatic tags do not move RAW records to TAGGED or qualify code for reuse.

## Explicit rules

All decisions use the relative file path only, without reading file contents,
calling an LLM, consulting the environment, or accessing a database.
Backslashes normalize to slashes. Absolute paths and parent traversal are rejected.
Role matching is case-insensitive. Component tags preserve case, deduplicate
repeated directory names, and exclude the filename. Root files have no component
tag. These labels describe literal directories, not inferred architectural roles.

Language uses the explicit suffix table in `src/repoharvester/tags.py`, preserved
from the previous record builder. Unknown suffixes produce `language:unknown`
and keep the record's `language=None`. For example, `.h` remains the baseline C
label; it is not content-verified and can also occur in C++ repositories.

Exactly one `role:` tag is selected, in this precedence order:

1. **docs**: directory `doc`, `docs`, or `documentation`; suffix `.md`, `.rst`,
   or `.adoc`; or exact filename `readme`, `license`, or `changelog`.
2. **test**: directory `test`, `tests`, or `__tests__`; filename beginning
   `test_`, ending `_test.py`, or containing `.test.` or `.spec.`.
3. **config**: directory `config`, `configs`, or `.github`; suffix `.toml`,
   `.ini`, or `.cfg`; or an exact filename from `_CONFIG_NAMES` in the module.
4. **source**: directory `src`, `source`, or `lib`; or a recognized language
   except JSON, YAML, TOML, and Markdown.
5. **unknown**: no rule matched.

Thus `tests/README.md` is docs, `tests/config/helper.py` is test,
`docs/example.py` is docs, and `fixtures/data.json` remains unknown.
Path-based labels are conventions with explicit limits, not semantic assertions.

Example for `src/app.py`:

```json
{"tags": ["language:Python", "path-component:src", "role:source"],
 "tag_ruleset": "path-baseline-v1", "qualification_state": "RAW"}
```

Any rule change must use a new ruleset version. This slice adds no persistence,
LLM interpretation, qualification promotion, or upstream gitingest changes.
The next bounded slice is SQLite storage and exact provenance/tag queries.
