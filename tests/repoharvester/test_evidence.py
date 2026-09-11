"""Tests for RepoHarvester's structured-evidence boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitingest.ingestion import ingest_query
from gitingest.schemas import FileSystemNode, FileSystemNodeType
from repoharvester import build_evidence_tree

if TYPE_CHECKING:
    from pathlib import Path

    from gitingest.schemas import IngestionQuery


def _collect_paths(node: FileSystemNode) -> set[str]:
    """Collect repository-relative paths using the portable comparison form."""
    paths = {node.path_str.replace("\\", "/")}
    for child in node.children:
        paths.update(_collect_paths(child))
    return paths


def test_structured_evidence_preserves_existing_flattened_output(
    temp_directory: Path,
    sample_query: IngestionQuery,
) -> None:
    """Expose FileSystemNode evidence without changing gitingest's tuple contract."""
    sample_query.local_path = temp_directory
    sample_query.subpath = "/"
    sample_query.type = None

    expected_files = {
        "src/subfile1.txt",
        "src/subfile2.py",
        "src/subdir/file_subdir.txt",
        "src/subdir/file_subdir.py",
        "file1.txt",
        "file2.py",
        "dir1/file_dir1.txt",
        "dir2/file_dir2.txt",
    }

    evidence = build_evidence_tree(sample_query)

    assert evidence.type == FileSystemNodeType.DIRECTORY
    assert evidence.file_count == len(expected_files)
    assert expected_files.issubset(_collect_paths(evidence))

    summary, tree, content = ingest_query(sample_query)

    assert f"Files analyzed: {len(expected_files)}" in summary
    assert "Directory structure:" in tree
    for expected_path in expected_files:
        assert expected_path in content
