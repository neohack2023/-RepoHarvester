"""Convert structured gitingest evidence into file-level harvest records."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from gitingest.schemas import FileSystemNode, FileSystemNodeType

from repoharvester.evidence import build_evidence_tree
from repoharvester.models import HarvestRecord
from repoharvester.provenance import resolve_checked_out_revision

if TYPE_CHECKING:
    from gitingest.schemas import IngestionQuery


_LANGUAGE_BY_SUFFIX = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".h": "C",
    ".hpp": "C++",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".ps1": "PowerShell",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}


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
        language=_LANGUAGE_BY_SUFFIX.get(Path(node.path_str).suffix.lower()),
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        representation_sha256=hashlib.sha256(representation.encode("utf-8")).hexdigest(),
        representation=representation,
    )
