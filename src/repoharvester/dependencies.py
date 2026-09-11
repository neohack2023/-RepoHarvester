"""Deterministic declared dependency evidence extraction."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable

from repoharvester.models import HarvestRecord, QualificationState

DEPENDENCY_EVIDENCE_RULESET = "package-json-dependencies-v1"
DEPENDENCY_EVIDENCE_UNIT_KIND = "evidence:declared-dependency"

_DEPENDENCY_SECTIONS = (
    ("dependencies", "runtime"),
    ("devDependencies", "development"),
)


class DependencyEvidenceError(ValueError):
    """Raised when an admitted dependency manifest cannot be parsed deterministically."""


def build_declared_dependency_records(file_records: Iterable[HarvestRecord]) -> list[HarvestRecord]:
    """Extract exact declared dependency evidence from a root ``package.json``.

    Version expressions are preserved verbatim. This function does not resolve packages,
    contact registries, inspect lockfiles, infer vulnerabilities, or change qualification.
    """
    records: list[HarvestRecord] = []
    for file_record in file_records:
        if file_record.unit_kind != "file" or file_record.path != "package.json":
            continue
        try:
            payload = json.loads(file_record.representation)
        except json.JSONDecodeError as exc:
            raise DependencyEvidenceError(f"invalid package.json JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise DependencyEvidenceError("package.json root must be a JSON object")

        for section_name, scope in _DEPENDENCY_SECTIONS:
            section = payload.get(section_name, {})
            if section is None:
                continue
            if not isinstance(section, dict):
                raise DependencyEvidenceError(f"package.json {section_name} must be a JSON object")
            for package_name, version_expression in section.items():
                if not isinstance(package_name, str) or not package_name:
                    raise DependencyEvidenceError(f"package.json {section_name} contains an invalid package name")
                if not isinstance(version_expression, str) or not version_expression:
                    raise DependencyEvidenceError(
                        f"package.json {section_name}.{package_name} must be a non-empty string"
                    )
                representation_sha256 = hashlib.sha256(version_expression.encode("utf-8")).hexdigest()
                records.append(
                    HarvestRecord(
                        source_repository=file_record.source_repository,
                        source_revision=file_record.source_revision,
                        path=file_record.path,
                        unit_kind=DEPENDENCY_EVIDENCE_UNIT_KIND,
                        unit_identity=(
                            f"package-json:{section_name}:{package_name}:{version_expression}"
                        ),
                        symbol_name=package_name,
                        language=None,
                        source_sha256=file_record.source_sha256,
                        representation_sha256=representation_sha256,
                        representation=version_expression,
                        qualification_state=QualificationState.RAW,
                        tags=tuple(
                            sorted(
                                {
                                    "evidence:declared-dependency",
                                    f"dependency:name:{package_name}",
                                    f"dependency:scope:{scope}",
                                    f"dependency:ruleset:{DEPENDENCY_EVIDENCE_RULESET}",
                                }
                            )
                        ),
                        tag_ruleset=DEPENDENCY_EVIDENCE_RULESET,
                    )
                )
    return sorted(records, key=lambda record: (record.path, record.unit_identity))
