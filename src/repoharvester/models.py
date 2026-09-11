"""Core record models for RepoHarvester."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QualificationState(str, Enum):
    """Lifecycle state for harvested material."""

    RAW = "RAW"
    CANDIDATE = "CANDIDATE"
    TAGGED = "TAGGED"
    VERIFIED = "VERIFIED"
    REUSABLE = "REUSABLE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ResolutionState(str, Enum):
    """Deterministic relationship target-resolution state."""

    EXACT = "EXACT"
    UNRESOLVED = "UNRESOLVED"
    EXTERNAL = "EXTERNAL"


@dataclass(frozen=True)
class HarvestRecord:
    """One provenance-backed harvested file or code-unit record."""

    source_repository: str
    source_revision: str
    path: str
    unit_kind: str
    language: str | None
    source_sha256: str
    representation_sha256: str
    representation: str
    qualification_state: QualificationState = QualificationState.RAW
    tags: tuple[str, ...] = ()
    tag_ruleset: str | None = None
    unit_identity: str = ""
    symbol_name: str | None = None
    start_byte: int | None = None
    end_byte: int | None = None
    start_row: int | None = None
    start_column: int | None = None
    end_row: int | None = None
    end_column: int | None = None


@dataclass(frozen=True)
class HarvestRelationship:
    """One deterministic directed relationship backed by source evidence."""

    source_repository: str
    source_revision: str
    source_path: str
    source_unit_kind: str
    source_unit_identity: str
    relationship_kind: str
    target_path: str = ""
    target_unit_kind: str = ""
    target_unit_identity: str = ""
    literal_target: str = ""
    resolution_state: ResolutionState = ResolutionState.UNRESOLVED
    start_byte: int | None = None
    end_byte: int | None = None
    start_row: int | None = None
    start_column: int | None = None
    end_row: int | None = None
    end_column: int | None = None
    extractor_name: str = ""
    extractor_version: str = ""
