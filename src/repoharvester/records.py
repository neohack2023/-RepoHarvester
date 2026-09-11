"""Convert structured gitingest evidence into file-level harvest records."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Iterator

from gitingest.schemas import FileSystemNode, FileSystemNodeType

from repoharvester.evidence import build_evidence_tree
from repoharvester.models import HarvestRecord
from repoharvester.provenance import resolve_checked_out_revision
from repoharvester.tags import BASELINE_TAG_RULESET, baseline_tags, language_for_path

if TYPE_CHECKING:
    from gitingest.schemas import IngestionQuery




def build_file_harvest_records(query: IngestionQuery) -> list[HarvestRecord]:
    """Build RAW file records from gitingest's structured evidence tree."""
    evidence = build_evidence_tree(query)
    revision = resolve_checked_out_revision(query.local_path)
    repository = query.url or query.slug

    return [
        _record_from_node(node, source_repository=repository, source_revision=revision)
        for node in _iter_file_nodes(evidence)
    ]


def _iter_file_nodes(node: FileSystemNode) -> Iterator[FileSystemNode]:
    if node.type == FileSystemNodeType.FILE:
        yield node
        return

    for child in node.children:
        yield from _iter_file_nodes(child)


def _record_from_node(node: FileSystemNode, *, source_repository: str, source_revision: str) -> HarvestRecord:
    source_bytes = node.path.read_bytes()
    representation = node.content

    return HarvestRecord(
        source_repository=source_repository,
        source_revision=source_revision,
        path=node.path_str.replace("\\", "/"),
        unit_kind="file",
        language=language_for_path(node.path_str),
        tags=baseline_tags(node.path_str),
        tag_ruleset=BASELINE_TAG_RULESET,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        representation_sha256=hashlib.sha256(representation.encode("utf-8")).hexdigest(),
        representation=representation,
    )
