"""Structured source-evidence access for RepoHarvester."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitingest.ingestion import build_file_system_tree
from gitingest.schemas import FileSystemNode

if TYPE_CHECKING:
    from gitingest.schemas import IngestionQuery


def build_evidence_tree(query: IngestionQuery) -> FileSystemNode:
    """Return gitingest's structured source tree without flattening it.

    RepoHarvester deliberately treats this tree as raw source evidence. Classification, qualification, persistence,
    and reusable-knowledge promotion belong to later layers and must not mutate the upstream extraction result.
    """
    return build_file_system_tree(query)
