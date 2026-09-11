"""Deterministic repository-license evidence tests."""

from __future__ import annotations

import hashlib

from repoharvester import HarvestRecord, QualificationState, build_repository_license_records

MIT_TEXT = """MIT License

Copyright (c) 2026 Example Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _file_record(path: str, text: str) -> HarvestRecord:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return HarvestRecord(
        source_repository="https://example.invalid/acme/repo.git",
        source_revision="a" * 40,
        path=path,
        unit_kind="file",
        language=None,
        source_sha256=digest,
        representation_sha256=digest,
        representation=text,
        qualification_state=QualificationState.RAW,
    )


def test_root_mit_license_becomes_raw_provenance_backed_evidence() -> None:
    source = _file_record("LICENSE", MIT_TEXT)

    records = build_repository_license_records([source])

    assert len(records) == 1
    record = records[0]
    assert record.source_repository == source.source_repository
    assert record.source_revision == source.source_revision
    assert record.path == "LICENSE"
    assert record.unit_kind == "evidence:repository-license"
    assert record.source_sha256 == source.source_sha256
    assert record.representation == MIT_TEXT
    assert record.qualification_state is QualificationState.RAW
    assert "evidence:repository-license" in record.tags
    assert "license:spdx:MIT" in record.tags
    assert "license:ruleset:repository-license-v1" in record.tags


def test_unknown_license_text_is_preserved_without_guessing() -> None:
    records = build_repository_license_records([_file_record("COPYING", "Custom terms only.\n")])

    assert len(records) == 1
    assert "license:spdx:UNKNOWN" in records[0].tags
    assert records[0].representation == "Custom terms only.\n"


def test_nested_license_and_non_license_files_are_not_repository_license_evidence() -> None:
    records = build_repository_license_records(
        [
            _file_record("vendor/LICENSE", MIT_TEXT),
            _file_record("README.md", MIT_TEXT),
        ]
    )

    assert records == []


def test_mit_title_without_full_canonical_clauses_is_not_normalized() -> None:
    records = build_repository_license_records(
        [_file_record("LICENSE.md", "MIT License\n\nCopyright (c) 2026 Example\n\nPermission granted.\n")]
    )

    assert len(records) == 1
    assert "license:spdx:UNKNOWN" in records[0].tags
