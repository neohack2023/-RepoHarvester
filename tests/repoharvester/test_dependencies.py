"""Deterministic package dependency evidence tests."""

from __future__ import annotations

import hashlib

import pytest

from repoharvester import (
    DependencyEvidenceError,
    HarvestRecord,
    QualificationState,
    build_declared_dependency_records,
)


def _file_record(path: str, text: str) -> HarvestRecord:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path=path,
        unit_kind="file",
        language="JSON" if path.endswith(".json") else None,
        source_sha256=digest,
        representation_sha256=digest,
        representation=text,
        qualification_state=QualificationState.RAW,
    )


def test_root_package_json_emits_runtime_and_development_dependency_evidence() -> None:
    manifest = _file_record(
        "package.json",
        '{"dependencies":{"zod":"^3.23.0","kuzu":"^0.11.3"},'
        '"devDependencies":{"@types/node":"^20.14.0"},'
        '"trustedDependencies":["kuzu"]}',
    )

    records = build_declared_dependency_records([manifest])

    assert [(record.symbol_name, record.representation) for record in records] == [
        ("@types/node", "^20.14.0"),
        ("kuzu", "^0.11.3"),
        ("zod", "^3.23.0"),
    ]
    runtime = next(record for record in records if record.symbol_name == "kuzu")
    development = next(record for record in records if record.symbol_name == "@types/node")
    assert runtime.source_sha256 == manifest.source_sha256
    assert runtime.qualification_state is QualificationState.RAW
    assert "dependency:scope:runtime" in runtime.tags
    assert "dependency:scope:development" in development.tags
    assert all(record.unit_kind == "evidence:declared-dependency" for record in records)
    assert all("trusted" not in record.unit_identity for record in records)


def test_version_expression_is_preserved_verbatim() -> None:
    manifest = _file_record("package.json", '{"dependencies":{"pkg":"workspace:^1.2.3 || >=2"}}')

    records = build_declared_dependency_records([manifest])

    assert len(records) == 1
    assert records[0].representation == "workspace:^1.2.3 || >=2"


def test_nested_package_json_is_not_admitted() -> None:
    records = build_declared_dependency_records(
        [_file_record("vendor/package.json", '{"dependencies":{"pkg":"1.0.0"}}')]
    )

    assert records == []


@pytest.mark.parametrize(
    "text",
    [
        "{broken",
        "[]",
        '{"dependencies":[]}',
        '{"dependencies":{"pkg":3}}',
    ],
)
def test_invalid_admitted_manifest_fails_closed(text: str) -> None:
    with pytest.raises(DependencyEvidenceError):
        build_declared_dependency_records([_file_record("package.json", text)])
