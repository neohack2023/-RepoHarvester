"""Tests for provenance-backed file harvest records."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import git
import pytest

from repoharvester import QualificationState, build_file_harvest_records

if TYPE_CHECKING:
    from pathlib import Path

    from gitingest.schemas import IngestionQuery


def _commit_fixture(path: Path) -> str:
    repo = git.Repo.init(path)
    actor = git.Actor("RepoHarvester Tests", "repoharvester@example.invalid")
    repo.git.add(A=True)
    repo.index.commit("fixture", author=actor, committer=actor)
    return repo.head.commit.hexsha


def test_file_harvest_records_capture_actual_revision_and_hashes(
    temp_directory: Path,
    sample_query: IngestionQuery,
) -> None:
    """Records use checked-out HEAD and distinguish raw bytes from representations."""
    expected_revision = _commit_fixture(temp_directory)
    sample_query.local_path = temp_directory
    sample_query.url = "https://example.invalid/source/repo.git"
    sample_query.commit = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    records = build_file_harvest_records(sample_query)
    records_by_path = {record.path: record for record in records}

    assert len(records) == 8
    assert {record.source_revision for record in records} == {expected_revision}
    assert all(record.source_revision != sample_query.commit for record in records)
    assert all(record.source_repository == sample_query.url for record in records)
    assert all(record.unit_kind == "file" for record in records)
    assert all(record.qualification_state == QualificationState.RAW for record in records)

    python_record = records_by_path["file2.py"]
    source_bytes = (temp_directory / "file2.py").read_bytes()
    representation = "print('Hello')"

    assert python_record.language == "Python"
    assert python_record.source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert python_record.representation == representation
    assert python_record.representation_sha256 == hashlib.sha256(representation.encode("utf-8")).hexdigest()


def test_file_harvest_records_require_git_provenance(
    temp_directory: Path,
    sample_query: IngestionQuery,
) -> None:
    """Unversioned source cannot silently become reproducible harvest material."""
    sample_query.local_path = temp_directory

    with pytest.raises(ValueError, match="resolvable Git HEAD"):
        build_file_harvest_records(sample_query)
