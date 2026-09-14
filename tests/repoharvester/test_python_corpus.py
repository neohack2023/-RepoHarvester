"""Integration test for Python code-unit harvesting into SQLite."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import git

from gitingest.schemas import IngestionQuery
from repoharvester.corpus import harvest_into_corpus
from repoharvester.storage import SQLiteHarvestStore


def test_python_symbols_round_trip_through_corpus(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "pkg" / "memory.py").write_text(
        "MAX_ITEMS = 10\n\nclass Memory:\n    def recall(self, key: str) -> str:\n        return key\n",
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
    query = IngestionQuery(
        local_path=root,
        url="https://example.invalid/python-memory.git",
        slug="python-memory",
        id=uuid4(),
        commit=revision,
        ignore_patterns={".git", "__pycache__"},
    )
    database = tmp_path / "corpus.sqlite3"

    result = harvest_into_corpus(query, database)
    stored = SQLiteHarvestStore(database).query_records(
        source_repository=query.url,
        source_revision=query.commit,
    )

    symbols = [record for record in stored if record.unit_kind.startswith("symbol:")]
    assert [(record.unit_kind, record.symbol_name) for record in symbols] == [
        ("symbol:constant", "MAX_ITEMS"),
        ("symbol:class", "Memory"),
        ("symbol:method", "recall"),
    ]
    assert result.summary["receipt_verified"] is True
    assert result.summary["semantic_skip_count"] == 0
    assert result.summary["qualification_state"] == "RAW"
    assert result.summary["relationship_kinds"]["contains"] == 3
