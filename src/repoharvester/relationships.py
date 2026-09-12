"""Deterministic TypeScript relationship extraction."""

from __future__ import annotations

import json
import posixpath
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from repoharvester.models import HarvestRecord, HarvestRelationship, ResolutionState

TYPESCRIPT_RELATIONSHIP_RULESET = "typescript-relationships-v1"
EXTRACTOR_NAME = "tree-sitter-typescript"
EXTRACTOR_VERSION = "0.21.2"

_TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")
_TSX_LANGUAGE = Language(tstypescript.language_tsx(), "tsx")


@dataclass(frozen=True)
class _TsconfigAliasConfig:
    """Bounded root-tsconfig alias mapping used only for local resolution."""

    base_url: str
    paths: tuple[tuple[str, tuple[str, ...]], ...]


def _language_for_path(path: str) -> Language:
    """Select the deterministic Tree-sitter grammar from the file suffix."""
    return _TSX_LANGUAGE if path.lower().endswith(".tsx") else _TYPESCRIPT_LANGUAGE


def build_typescript_relationships(
    records: Iterable[HarvestRecord],
    *,
    skip_source_paths: Iterable[str] = (),
) -> list[HarvestRelationship]:
    """Build deterministic containment and import relationships for TypeScript records.

    ``skip_source_paths`` is used by the generic corpus harvester when the pinned
    parser cannot represent one source file. The file remains available as an
    import target, but no semantic relationships are fabricated from that file.
    """
    materialized = list(records)
    skipped = frozenset(skip_source_paths)
    alias_config = _root_tsconfig_alias_config(materialized)
    file_records = [
        record for record in materialized if record.unit_kind == "file" and record.language == "TypeScript"
    ]
    symbols_by_path: dict[str, list[HarvestRecord]] = defaultdict(list)
    files_by_path = {record.path: record for record in file_records}
    for record in materialized:
        if record.path in files_by_path and record.unit_kind.startswith("symbol:"):
            symbols_by_path[record.path].append(record)

    relationships: list[HarvestRelationship] = []
    for file_record in file_records:
        for symbol in sorted(symbols_by_path[file_record.path], key=lambda item: item.unit_identity):
            relationships.append(
                HarvestRelationship(
                    source_repository=file_record.source_repository,
                    source_revision=file_record.source_revision,
                    source_path=file_record.path,
                    source_unit_kind=file_record.unit_kind,
                    source_unit_identity=file_record.unit_identity,
                    relationship_kind="contains",
                    target_path=symbol.path,
                    target_unit_kind=symbol.unit_kind,
                    target_unit_identity=symbol.unit_identity,
                    resolution_state=ResolutionState.EXACT,
                    start_byte=symbol.start_byte,
                    end_byte=symbol.end_byte,
                    start_row=symbol.start_row,
                    start_column=symbol.start_column,
                    end_row=symbol.end_row,
                    end_column=symbol.end_column,
                    extractor_name=EXTRACTOR_NAME,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )
        if file_record.path not in skipped:
            relationships.extend(_import_relationships(file_record, files_by_path, alias_config))

    return sorted(relationships, key=_relationship_sort_key)


def _root_tsconfig_alias_config(records: Iterable[HarvestRecord]) -> _TsconfigAliasConfig | None:
    """Read one strict-JSON root tsconfig baseUrl/paths without compiler emulation.

    The bounded adapter activates only when ``tsconfig.json`` is the repository's
    sole ``tsconfig*.json`` file. Multiple configs, ``extends``, and project
    references require config-scope semantics that are intentionally deferred;
    those repositories therefore keep non-relative imports EXTERNAL rather than
    accepting a guessed root mapping. JSONC preprocessing, package/workspace
    resolution, and compiler execution are also out of scope for this ruleset.
    """
    file_records = [record for record in records if record.unit_kind == "file"]
    config_paths = sorted(
        record.path
        for record in file_records
        if _is_tsconfig_json_path(record.path)
    )
    if config_paths != ["tsconfig.json"]:
        return None

    config = next(record for record in file_records if record.path == "tsconfig.json")
    try:
        payload = json.loads(config.representation)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if "extends" in payload or payload.get("references"):
        return None

    compiler_options = payload.get("compilerOptions", {})
    if not isinstance(compiler_options, dict):
        return None
    raw_paths = compiler_options.get("paths")
    if not isinstance(raw_paths, dict) or not raw_paths:
        return None

    raw_base_url = compiler_options.get("baseUrl", ".")
    if not isinstance(raw_base_url, str) or not raw_base_url:
        return None
    base_url = posixpath.normpath(raw_base_url.replace("\\", "/"))
    if not _is_repository_local_path(base_url):
        return None

    paths: list[tuple[str, tuple[str, ...]]] = []
    for pattern, replacements in raw_paths.items():
        if not isinstance(pattern, str) or not pattern or pattern.count("*") > 1:
            return None
        if not isinstance(replacements, list) or not replacements:
            return None
        normalized_replacements: list[str] = []
        for replacement in replacements:
            if not isinstance(replacement, str) or not replacement or replacement.count("*") > 1:
                return None
            normalized = replacement.replace("\\", "/")
            candidate_root = posixpath.normpath(posixpath.join(base_url, normalized.replace("*", "placeholder")))
            if not _is_repository_local_path(candidate_root):
                return None
            normalized_replacements.append(normalized)
        paths.append((pattern, tuple(normalized_replacements)))

    return _TsconfigAliasConfig(base_url=base_url, paths=tuple(paths))


def _is_tsconfig_json_path(path: str) -> bool:
    name = posixpath.basename(path).lower()
    return name.startswith("tsconfig") and name.endswith(".json")


def _is_repository_local_path(path: str) -> bool:
    return path not in {"", ".."} and not path.startswith("../") and not posixpath.isabs(path)


def _import_relationships(
    file_record: HarvestRecord,
    files_by_path: dict[str, HarvestRecord],
    alias_config: _TsconfigAliasConfig | None,
) -> list[HarvestRelationship]:
    source = file_record.representation.encode("utf-8")
    parser = Parser()
    parser.set_language(_language_for_path(file_record.path))
    tree = parser.parse(source)
    if tree.root_node.has_error:
        message = f"cannot deterministically extract relationships from parse-error file: {file_record.path}"
        raise ValueError(message)

    relationships: list[HarvestRelationship] = []
    for node in tree.root_node.named_children:
        if node.type != "import_statement":
            continue
        string_node = node.child_by_field_name("source") or _first_named_child(node, "string")
        if string_node is None:
            raise ValueError(f"import statement at byte {node.start_byte} has no module specifier")
        literal = source[string_node.start_byte : string_node.end_byte].decode("utf-8")
        module_specifier = _unquote(literal)
        target_path, state = _resolve_module(
            file_record.path,
            module_specifier,
            files_by_path,
            alias_config=alias_config,
        )
        target = files_by_path.get(target_path) if target_path else None
        relationships.append(
            HarvestRelationship(
                source_repository=file_record.source_repository,
                source_revision=file_record.source_revision,
                source_path=file_record.path,
                source_unit_kind=file_record.unit_kind,
                source_unit_identity=file_record.unit_identity,
                relationship_kind="imports",
                target_path=target.path if target else "",
                target_unit_kind=target.unit_kind if target else "",
                target_unit_identity=target.unit_identity if target else "",
                literal_target=literal,
                resolution_state=state,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                start_row=node.start_point[0],
                start_column=node.start_point[1],
                end_row=node.end_point[0],
                end_column=node.end_point[1],
                extractor_name=EXTRACTOR_NAME,
                extractor_version=EXTRACTOR_VERSION,
            )
        )
    return relationships


def _first_named_child(node: Node, node_type: str) -> Node | None:
    return next((child for child in node.named_children if child.type == node_type), None)


def _unquote(literal: str) -> str:
    if len(literal) >= 2 and literal[0] == literal[-1] and literal[0] in {"'", '"'}:
        return literal[1:-1]
    return literal


def _resolve_module(
    source_path: str,
    module_specifier: str,
    files_by_path: dict[str, HarvestRecord],
    *,
    alias_config: _TsconfigAliasConfig | None = None,
) -> tuple[str, ResolutionState]:
    if module_specifier.startswith("."):
        base = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), module_specifier))
        return _resolve_candidates(_typescript_path_candidates(base), files_by_path, ResolutionState.UNRESOLVED)

    alias_candidates = _alias_path_candidates(module_specifier, alias_config)
    if alias_candidates is None:
        return "", ResolutionState.EXTERNAL
    return _resolve_candidates(alias_candidates, files_by_path, ResolutionState.UNRESOLVED)


def _resolve_candidates(
    candidates: Iterable[str],
    files_by_path: dict[str, HarvestRecord],
    miss_state: ResolutionState,
) -> tuple[str, ResolutionState]:
    for candidate in candidates:
        if candidate in files_by_path:
            return candidate, ResolutionState.EXACT
    return "", miss_state


def _typescript_path_candidates(base: str) -> tuple[str, ...]:
    candidates = [base]
    if not posixpath.splitext(base)[1]:
        candidates.extend(
            [
                f"{base}.ts",
                f"{base}.tsx",
                posixpath.join(base, "index.ts"),
                posixpath.join(base, "index.tsx"),
            ]
        )
    return tuple(candidates)


def _alias_path_candidates(
    module_specifier: str,
    alias_config: _TsconfigAliasConfig | None,
) -> tuple[str, ...] | None:
    if alias_config is None:
        return None

    matches: list[tuple[int, int, str, tuple[str, ...], str]] = []
    for pattern, replacements in alias_config.paths:
        if "*" not in pattern:
            if module_specifier == pattern:
                matches.append((0, -len(pattern), pattern, replacements, ""))
            continue

        prefix, suffix = pattern.split("*", 1)
        if not module_specifier.startswith(prefix) or not module_specifier.endswith(suffix):
            continue
        if len(module_specifier) < len(prefix) + len(suffix):
            continue
        wildcard = module_specifier[len(prefix) : len(module_specifier) - len(suffix) if suffix else None]
        matches.append((1, -(len(prefix) + len(suffix)), pattern, replacements, wildcard))

    if not matches:
        return None

    _, _, _, replacements, wildcard = sorted(matches, key=lambda item: item[:3])[0]
    candidates: list[str] = []
    for replacement in replacements:
        substituted = replacement.replace("*", wildcard)
        base = posixpath.normpath(posixpath.join(alias_config.base_url, substituted))
        if not _is_repository_local_path(base):
            continue
        candidates.extend(_typescript_path_candidates(base))
    return tuple(dict.fromkeys(candidates))


def _relationship_sort_key(relationship: HarvestRelationship) -> tuple[object, ...]:
    return (
        relationship.source_repository,
        relationship.source_revision,
        relationship.source_path,
        relationship.source_unit_kind,
        relationship.source_unit_identity,
        relationship.relationship_kind,
        relationship.target_path,
        relationship.target_unit_kind,
        relationship.target_unit_identity,
        relationship.literal_target,
        relationship.start_byte if relationship.start_byte is not None else -1,
        relationship.end_byte if relationship.end_byte is not None else -1,
    )
