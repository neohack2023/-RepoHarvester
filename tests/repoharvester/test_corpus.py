"""Tests for generic multi-repository corpus harvesting."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import git

from gitingest.schemas import IngestionQuery
from repoharvester.corpus import harvest_into_corpus
from repoharvester.models import HarvestRecord, QualificationState
from repoharvester.storage import SQLiteHarvestStore


def _fixture_query(
    root: Path,
    name: str,
    source: str,
    *,
    extra_sources: dict[str, str] | None = None,
) -> IngestionQuery:
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "index.ts").write_text(source, encoding="utf-8")
    for relative_path, extra_source in (extra_sources or {}).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(extra_source, encoding="utf-8")
    (root / "package.json").write_text(
        '{"name":"' + name + '","devDependencies":{"typescript":"^5.5.0"}}\n',
        encoding="utf-8",
    )
    (root / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, subject to the following conditions:\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n",
        encoding="utf-8",
    )
    repo = git.Repo.init(root)
    actor = git.Actor("RepoHarvester Tests", "repoharvester@example.invalid")
    repo.git.add(A=True)
    repo.index.commit("fixture", author=actor, committer=actor)
    revision = repo.head.commit.hexsha
    return IngestionQuery(
        local_path=root,
        url=f"https://example.invalid/{name}.git",
        slug=name,
        id=uuid4(),
        commit=revision,
        ignore_patterns={".git", "node_modules"},
    )


def _record_identity(record: HarvestRecord) -> tuple[str, str, str, str, str]:
    """Return the durable corpus identity independent of query result ordering."""
    return (
        record.source_repository,
        record.source_revision,
        record.path,
        record.unit_kind,
        record.unit_identity,
    )


def _records_by_identity(
    records: list[HarvestRecord] | tuple[HarvestRecord, ...],
) -> dict[tuple[str, str, str, str, str], HarvestRecord]:
    return {_record_identity(record): record for record in records}


def test_shared_corpus_preserves_multiple_repositories(tmp_path: Path) -> None:
    database = tmp_path / "corpus.sqlite3"
    first = _fixture_query(
        tmp_path / "first",
        "first",
        "export function clamp(value: number): number { return Math.max(0, value); }\n",
    )
    second = _fixture_query(
        tmp_path / "second",
        "second",
        "export function double(value: number): number { return value * 2; }\n",
    )

    first_result = harvest_into_corpus(first, database)
    second_result = harvest_into_corpus(second, database)

    store = SQLiteHarvestStore(database)
    stored_first = store.query_records(source_repository=first.url, source_revision=first.commit)
    stored_second = store.query_records(source_repository=second.url, source_revision=second.commit)

    # SQLite is free to return independently inserted evidence classes in a different
    # row order. The corpus contract is identity + content preservation, not incidental
    # SELECT ordering.
    assert _records_by_identity(stored_first) == _records_by_identity(first_result.records)
    assert _records_by_identity(stored_second) == _records_by_identity(second_result.records)
    assert all(record.qualification_state == QualificationState.RAW for record in stored_first)
    assert all(record.qualification_state == QualificationState.RAW for record in stored_second)
    assert first_result.summary["qualification_performed"] is False
    assert second_result.summary["qualification_performed"] is False


def test_reharvest_is_idempotent_for_same_repository_revision(tmp_path: Path) -> None:
    database = tmp_path / "corpus.sqlite3"
    query = _fixture_query(
        tmp_path / "source",
        "same",
        "export const answer = (): number => 42;\n",
    )

    first = harvest_into_corpus(query, database)
    second = harvest_into_corpus(query, database)

    store = SQLiteHarvestStore(database)
    stored = store.query_records(source_repository=query.url, source_revision=query.commit)

    assert first.records == second.records
    assert first.receipt.manifest_sha256 == second.receipt.manifest_sha256
    assert len(stored) == len(first.records)


def test_parse_error_file_keeps_raw_file_evidence_and_warns(tmp_path: Path) -> None:
    database = tmp_path / "corpus.sqlite3"
    query = _fixture_query(
        tmp_path / "partial",
        "partial",
        "export function healthy(): number { return 1; }\n",
        extra_sources={"src/broken.ts": "export const broken = ;\n"},
    )

    result = harvest_into_corpus(query, database)

    broken_file = [
        record
        for record in result.records
        if record.path == "src/broken.ts" and record.unit_kind == "file"
    ]
    healthy_symbols = [
        record
        for record in result.records
        if record.path == "src/index.ts" and record.unit_kind == "symbol:function"
    ]

    assert len(broken_file) == 1
    assert broken_file[0].qualification_state == QualificationState.RAW
    assert len(healthy_symbols) == 1
    assert result.summary["semantic_skip_count"] == 1
    assert result.summary["semantic_skipped_paths"] == ["src/broken.ts"]
    assert result.summary["warnings"] == [
        "semantic-extraction-skipped:src/broken.ts:typescript-parse-error"
    ]
    assert result.receipt.warnings == (
        "semantic-extraction-skipped:src/broken.ts:typescript-parse-error",
    )
    assert all(
        relationship.source_path != "src/broken.ts"
        for relationship in result.relationships
    )
