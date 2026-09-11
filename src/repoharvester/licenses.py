"""Deterministic repository-level license evidence extraction."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from repoharvester.models import HarvestRecord, QualificationState

LICENSE_EVIDENCE_RULESET = "repository-license-v1"
LICENSE_EVIDENCE_UNIT_KIND = "evidence:repository-license"

_ROOT_LICENSE_FILENAMES = frozenset(
    {
        "license",
        "license.txt",
        "license.md",
        "copying",
        "copying.txt",
        "copying.md",
    }
)

_MIT_PERMISSION = (
    "Permission is hereby granted, free of charge, to any person obtaining a copy "
    "of this software and associated documentation files (the \"Software\"), to deal "
    "in the Software without restriction, including without limitation the rights "
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
    "copies of the Software, and to permit persons to whom the Software is "
    "furnished to do so, subject to the following conditions:"
)
_MIT_NOTICE = (
    "The above copyright notice and this permission notice shall be included in all "
    "copies or substantial portions of the Software."
)
_MIT_WARRANTY = (
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE "
    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER "
    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, "
    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE "
    "SOFTWARE."
)


def build_repository_license_records(file_records: list[HarvestRecord]) -> list[HarvestRecord]:
    """Build RAW repository-license evidence records from root conventional license files.

    The evidence record describes the license document itself. It does not infer that
    every harvested file is covered by that document and does not change qualification.
    """
    license_records: list[HarvestRecord] = []
    for file_record in file_records:
        if not _is_root_license_file(file_record):
            continue
        spdx_expression = _deterministic_spdx_expression(file_record.representation)
        spdx_tag = f"license:spdx:{spdx_expression or 'UNKNOWN'}"
        tags = tuple(
            sorted(
                {
                    "evidence:repository-license",
                    spdx_tag,
                    f"license:ruleset:{LICENSE_EVIDENCE_RULESET}",
                }
            )
        )
        license_records.append(
            HarvestRecord(
                source_repository=file_record.source_repository,
                source_revision=file_record.source_revision,
                path=file_record.path,
                unit_kind=LICENSE_EVIDENCE_UNIT_KIND,
                unit_identity=f"repository-license:{file_record.path}:{file_record.source_sha256}",
                language=None,
                source_sha256=file_record.source_sha256,
                representation_sha256=hashlib.sha256(file_record.representation.encode("utf-8")).hexdigest(),
                representation=file_record.representation,
                qualification_state=QualificationState.RAW,
                tags=tags,
                tag_ruleset=LICENSE_EVIDENCE_RULESET,
            )
        )
    return sorted(license_records, key=lambda record: (record.path, record.unit_identity))


def _is_root_license_file(record: HarvestRecord) -> bool:
    if record.unit_kind != "file":
        return False
    path = PurePosixPath(record.path)
    return path.parent == PurePosixPath(".") and path.name.lower() in _ROOT_LICENSE_FILENAMES


def _deterministic_spdx_expression(text: str) -> str | None:
    normalized = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    if not normalized.startswith("MIT License Copyright "):
        return None
    permission = " ".join(_MIT_PERMISSION.split())
    notice = " ".join(_MIT_NOTICE.split())
    warranty = " ".join(_MIT_WARRANTY.split())
    permission_index = normalized.find(permission)
    notice_index = normalized.find(notice)
    warranty_index = normalized.find(warranty)
    if 0 <= permission_index < notice_index < warranty_index and normalized.endswith(warranty):
        return "MIT"
    return None
