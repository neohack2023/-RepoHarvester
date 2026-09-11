"""Tests for deterministic extraction receipts and reproduction checks."""

from __future__ import annotations

import pytest

from repoharvester import HarvestRecord, QualificationState
from repoharvester.receipts import (
    build_extraction_receipt,
    load_extraction_receipt,
    verify_extraction_receipt,
    write_extraction_receipt,
)
from repoharvester.storage import SQLiteHarvestStore


def _record(path: str, **overrides) -> HarvestRecord:
    values = {
        "source_repository": "https://example.invalid/acme/repo.git",
        "source_revision": "a" * 40,
        "path": path,
        "unit_kind": "file",
        "language": "Python",
        "source_sha256": (path.encode("utf-8").hex() + "0" * 64)[:64],
        "representation_sha256": (path.encode("utf-8").hex() + "1" * 64)[:64],
        "representation": f"# {path}",
        "qualification_state": QualificationState.RAW,
        "tags": ("language:Python", "role:source"),
        "tag_ruleset": "path-baseline-v1",
    }
    values.update(overrides)
    return HarvestRecord(**values)


def test_receipt_is_order_independent_and_binds_manifest() -> None:
    first = _record("src/a.py")
    second = _record("src/b.py")

    forward = build_extraction_receipt([first, second])
    reverse = build_extraction_receipt([second, first])
    changed = build_extraction_receipt(
        [first, _record("src/b.py", tags=("language:Python", "role:test"))]
    )

    assert forward == reverse
    assert forward.manifest_sha256 != changed.manifest_sha256
    assert forward.record_count == 2
    assert forward.qualification_states == ("RAW",)


def test_receipt_rejects_empty_or_mixed_provenance() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_extraction_receipt([])

    with pytest.raises(ValueError, match="exactly one source repository and revision"):
        build_extraction_receipt(
            [_record("a.py"), _record("b.py", source_revision="b" * 40)]
        )


def test_receipt_round_trip_verifies_records_loaded_from_sqlite(tmp_path) -> None:
    store = SQLiteHarvestStore(tmp_path / "harvest.sqlite3")
    records = [_record("src/b.py"), _record("src/a.py")]
    store.upsert_records(records)
    stored = store.query_records(
        source_repository=records[0].source_repository,
        source_revision=records[0].source_revision,
    )

    receipt = build_extraction_receipt(stored, warnings=("fixture-only",))
    receipt_path = tmp_path / "EXTRACTION_RECEIPT.json"
    write_extraction_receipt(receipt_path, receipt)
    loaded = load_extraction_receipt(receipt_path)

    assert loaded == receipt
    assert verify_extraction_receipt(loaded, stored)
    assert not verify_extraction_receipt(
        loaded,
        [stored[0], _record("src/b.py", representation_sha256="f" * 64)],
    )
