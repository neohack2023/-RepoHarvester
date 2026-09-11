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


@dataclass(frozen=True)
class HarvestRecord:
    """One provenance-backed harvested unit."""

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
    start_line: int | None = None
    start_column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
