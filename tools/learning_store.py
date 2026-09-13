from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Mapping, Sequence

try:
    from tools.build_knowledge_db import DEFAULT_DB
    from tools.db_runtime import connect_runtime
    from tools.learning_threshold import (
        AUTHORITY_EFFECT,
        PROMOTION_STATE,
        CapabilityRecord,
        EvaluationReport,
        MaturityStage,
        ProcedureSpec,
    )
except ModuleNotFoundError:
    from build_knowledge_db import DEFAULT_DB
    from db_runtime import connect_runtime
    from learning_threshold import (
        AUTHORITY_EFFECT,
        PROMOTION_STATE,
        CapabilityRecord,
        EvaluationReport,
        MaturityStage,
        ProcedureSpec,
    )


class MemoryType(str, Enum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    NEGATIVE = "NEGATIVE"


@dataclass(frozen=True)
class ExperienceRecord:
    memory_id: str
    memory_type: MemoryType
    branch_scope: str
    statement: str
    source_evidence_refs: tuple[str, ...]
    procedure_id: str = ""
    capability_id: str = ""
    authority_effect: str = AUTHORITY_EFFECT
    promotion_state: str = PROMOTION_STATE


@dataclass(frozen=True)
class CapabilityLifecycleEvent:
    event_id: str
    capability_id: str
    branch_scope: str
    maturity_stage: MaturityStage
    procedure_ids: tuple[str, ...]
    transfer_fixture_ids: tuple[str, ...]
    evaluation_profile: tuple[tuple[str, bool], ...]
    created_at: str = ""
    event_sequence: int = 0
    episode_id: str = ""
    predecessor_event_id: str = ""
    evaluator_version: str = "learning-threshold:v1"
    authority_effect: str = AUTHORITY_EFFECT
    promotion_state: str = PROMOTION_STATE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def consolidate_experience(
    *,
    memory_type: MemoryType,
    branch_scope: str,
    statement: str,
    source_evidence_refs: Sequence[str],
    procedure_id: str = "",
    capability_id: str = "",
) -> ExperienceRecord:
    branch_scope = branch_scope.strip()
    statement = statement.strip()
    refs = tuple(sorted(set(ref.strip() for ref in source_evidence_refs if ref.strip())))
    if not branch_scope or not statement:
        raise ValueError("branch_scope and statement are required")
    if not refs:
        raise ValueError("experience consolidation requires addressable evidence")
    if memory_type == MemoryType.PROCEDURAL and not procedure_id.strip():
        raise ValueError("procedural memory requires procedure_id")

    payload = {
        "memory_type": memory_type.value,
        "branch_scope": branch_scope,
        "statement": statement,
        "source_evidence_refs": refs,
        "procedure_id": procedure_id.strip(),
        "capability_id": capability_id.strip(),
    }
    return ExperienceRecord(
        memory_id=_stable_id("memory", payload),
        memory_type=memory_type,
        branch_scope=branch_scope,
        statement=statement,
        source_evidence_refs=refs,
        procedure_id=procedure_id.strip(),
        capability_id=capability_id.strip(),
    )


class LearningStore:
    """Learning persistence projected into the shared DevOS SQLite runtime."""

    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return connect_runtime(self.db_path)

    def _ensure_schema(self) -> None:
        connection = self._connect()
        connection.close()

    def persist_procedure(self, procedure: ProcedureSpec) -> str:
        payload = _procedure_payload(procedure)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO learning_procedures
                    (procedure_id, branch_scope, payload_json, authority_effect,
                     promotion_state, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(procedure_id) DO UPDATE SET
                    branch_scope=excluded.branch_scope,
                    payload_json=excluded.payload_json,
                    authority_effect=excluded.authority_effect,
                    promotion_state=excluded.promotion_state
                """,
                (
                    procedure.procedure_id,
                    procedure.branch_scope,
                    _json(payload),
                    AUTHORITY_EFFECT,
                    PROMOTION_STATE,
                    _now(),
                ),
            )
            connection.execute(
                "DELETE FROM procedure_evidence WHERE procedure_id = ?",
                (procedure.procedure_id,),
            )
            connection.executemany(
                "INSERT INTO procedure_evidence(procedure_id, evidence_ref) VALUES (?, ?)",
                ((procedure.procedure_id, ref) for ref in procedure.source_evidence_refs),
            )
        return procedure.procedure_id

    def persist_evaluation(
        self,
        report: EvaluationReport,
        *,
        evaluator_version: str = "learning-threshold:v1",
    ) -> str:
        payload = _evaluation_payload(report)
        evaluation_id = _stable_id("evaluation", payload)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO learning_evaluations
                    (evaluation_id, procedure_id, payload_json, authority_effect,
                     promotion_state, created_at, evaluator_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id,
                    report.procedure_id,
                    _json(payload),
                    report.authority_effect,
                    report.promotion_state,
                    _now(),
                    evaluator_version,
                ),
            )
        return evaluation_id

    def persist_experience(self, record: ExperienceRecord) -> str:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO learning_experiences
                    (memory_id, memory_type, branch_scope, statement,
                     source_evidence_refs_json, procedure_id, capability_id,
                     authority_effect, promotion_state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.memory_type.value,
                    record.branch_scope,
                    record.statement,
                    _json(record.source_evidence_refs),
                    record.procedure_id,
                    record.capability_id,
                    record.authority_effect,
                    record.promotion_state,
                    _now(),
                ),
            )
            connection.execute(
                "DELETE FROM experience_evidence WHERE memory_id = ?",
                (record.memory_id,),
            )
            connection.executemany(
                "INSERT INTO experience_evidence(memory_id, evidence_ref) VALUES (?, ?)",
                ((record.memory_id, ref) for ref in record.source_evidence_refs),
            )
        return record.memory_id

    def persist_capability(
        self,
        capability: CapabilityRecord,
        *,
        episode_id: str = "",
        evaluator_version: str = "learning-threshold:v1",
    ) -> CapabilityLifecycleEvent:
        payload = _capability_payload(capability)
        with self._connect() as connection:
            previous = connection.execute(
                """
                SELECT event_id, event_sequence
                FROM learning_capability_events
                WHERE capability_id = ?
                ORDER BY event_sequence DESC, created_at DESC, event_id DESC
                LIMIT 1
                """,
                (capability.capability_id,),
            ).fetchone()
            sequence = (int(previous["event_sequence"]) + 1) if previous else 1
            predecessor = str(previous["event_id"]) if previous else ""
            created_at = _now()
            event_payload = {
                "capability_id": capability.capability_id,
                "branch_scope": capability.branch_scope,
                "maturity_stage": capability.maturity_stage.value,
                "procedure_ids": capability.procedure_ids,
                "transfer_fixture_ids": capability.transfer_fixture_ids,
                "evaluation_profile": capability.recent_eval_profile,
                "event_sequence": sequence,
                "episode_id": episode_id,
                "predecessor_event_id": predecessor,
                "evaluator_version": evaluator_version,
            }
            event = CapabilityLifecycleEvent(
                event_id=_stable_id("capability-event", event_payload),
                capability_id=capability.capability_id,
                branch_scope=capability.branch_scope,
                maturity_stage=capability.maturity_stage,
                procedure_ids=capability.procedure_ids,
                transfer_fixture_ids=capability.transfer_fixture_ids,
                evaluation_profile=capability.recent_eval_profile,
                created_at=created_at,
                event_sequence=sequence,
                episode_id=episode_id,
                predecessor_event_id=predecessor,
                evaluator_version=evaluator_version,
            )
            connection.execute(
                """
                INSERT INTO learning_capabilities
                    (capability_id, branch_scope, maturity_stage, payload_json,
                     authority_effect, promotion_state, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(capability_id) DO UPDATE SET
                    branch_scope=excluded.branch_scope,
                    maturity_stage=excluded.maturity_stage,
                    payload_json=excluded.payload_json,
                    authority_effect=excluded.authority_effect,
                    promotion_state=excluded.promotion_state,
                    updated_at=excluded.updated_at
                """,
                (
                    capability.capability_id,
                    capability.branch_scope,
                    capability.maturity_stage.value,
                    _json(payload),
                    capability.authority_effect,
                    capability.promotion_state,
                    created_at,
                ),
            )
            connection.execute(
                "DELETE FROM capability_procedures WHERE capability_id = ?",
                (capability.capability_id,),
            )
            connection.executemany(
                """
                INSERT INTO capability_procedures(capability_id, procedure_id, ordinal)
                VALUES (?, ?, ?)
                """,
                (
                    (capability.capability_id, procedure_id, ordinal)
                    for ordinal, procedure_id in enumerate(capability.procedure_ids)
                ),
            )
            connection.execute(
                "DELETE FROM capability_transfer_fixtures WHERE capability_id = ?",
                (capability.capability_id,),
            )
            connection.executemany(
                """
                INSERT INTO capability_transfer_fixtures(capability_id, fixture_id, ordinal)
                VALUES (?, ?, ?)
                """,
                (
                    (capability.capability_id, fixture_id, ordinal)
                    for ordinal, fixture_id in enumerate(capability.transfer_fixture_ids)
                ),
            )
            connection.execute(
                """
                INSERT INTO learning_capability_events
                    (event_id, capability_id, branch_scope, maturity_stage,
                     payload_json, authority_effect, promotion_state, created_at,
                     event_sequence, episode_id, predecessor_event_id, evaluator_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.capability_id,
                    event.branch_scope,
                    event.maturity_stage.value,
                    _json(asdict(event)),
                    event.authority_effect,
                    event.promotion_state,
                    event.created_at,
                    event.event_sequence,
                    event.episode_id,
                    event.predecessor_event_id,
                    event.evaluator_version,
                ),
            )
        return event

    def load_procedure(self, procedure_id: str) -> ProcedureSpec:
        row = self._one(
            "SELECT payload_json FROM learning_procedures WHERE procedure_id = ?",
            (procedure_id,),
        )
        payload = json.loads(row["payload_json"])
        return ProcedureSpec(
            branch_scope=payload["branch_scope"],
            name=payload["name"],
            version=payload["version"],
            trigger_conditions=tuple(payload["trigger_conditions"]),
            input_schema=tuple(payload["input_schema"]),
            output_schema=tuple(payload["output_schema"]),
            implementation_ref=payload["implementation_ref"],
            preconditions=tuple(payload["preconditions"]),
            known_failures=tuple(payload["known_failures"]),
            source_evidence_refs=tuple(payload["source_evidence_refs"]),
            rollback_ref=payload["rollback_ref"],
        )

    def load_capability(self, capability_id: str) -> CapabilityRecord:
        row = self._one(
            "SELECT payload_json FROM learning_capabilities WHERE capability_id = ?",
            (capability_id,),
        )
        payload = json.loads(row["payload_json"])
        return CapabilityRecord(
            capability_id=payload["capability_id"],
            branch_scope=payload["branch_scope"],
            description=payload["description"],
            procedure_ids=tuple(payload["procedure_ids"]),
            known_tasks=tuple(payload["known_tasks"]),
            known_failure_modes=tuple(payload["known_failure_modes"]),
            maturity_stage=MaturityStage(payload["maturity_stage"]),
            recent_eval_profile=tuple(
                (tier, passed) for tier, passed in payload["recent_eval_profile"]
            ),
            transfer_fixture_ids=tuple(payload["transfer_fixture_ids"]),
            authority_effect=payload["authority_effect"],
            promotion_state=payload["promotion_state"],
        )

    def list_experiences(
        self,
        *,
        branch_scope: str | None = None,
    ) -> tuple[ExperienceRecord, ...]:
        query = "SELECT * FROM learning_experiences"
        params: tuple[object, ...] = ()
        if branch_scope is not None:
            query += " WHERE branch_scope = ?"
            params = (branch_scope,)
        query += " ORDER BY memory_id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return tuple(
            ExperienceRecord(
                memory_id=row["memory_id"],
                memory_type=MemoryType(row["memory_type"]),
                branch_scope=row["branch_scope"],
                statement=row["statement"],
                source_evidence_refs=tuple(json.loads(row["source_evidence_refs_json"])),
                procedure_id=row["procedure_id"],
                capability_id=row["capability_id"],
                authority_effect=row["authority_effect"],
                promotion_state=row["promotion_state"],
            )
            for row in rows
        )

    def capability_history(
        self,
        capability_id: str,
    ) -> tuple[CapabilityLifecycleEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM learning_capability_events
                WHERE capability_id = ?
                ORDER BY event_sequence, created_at, event_id
                """,
                (capability_id,),
            ).fetchall()
        events: list[CapabilityLifecycleEvent] = []
        for row in rows:
            event_payload = json.loads(row["payload_json"])
            events.append(
                CapabilityLifecycleEvent(
                    event_id=row["event_id"],
                    capability_id=row["capability_id"],
                    branch_scope=row["branch_scope"],
                    maturity_stage=MaturityStage(row["maturity_stage"]),
                    procedure_ids=tuple(event_payload["procedure_ids"]),
                    transfer_fixture_ids=tuple(event_payload["transfer_fixture_ids"]),
                    evaluation_profile=tuple(
                        (tier, passed)
                        for tier, passed in event_payload["evaluation_profile"]
                    ),
                    created_at=row["created_at"],
                    event_sequence=row["event_sequence"],
                    episode_id=row["episode_id"],
                    predecessor_event_id=row["predecessor_event_id"],
                    evaluator_version=row["evaluator_version"],
                    authority_effect=row["authority_effect"],
                    promotion_state=row["promotion_state"],
                )
            )
        return tuple(events)

    def _one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            raise KeyError(params[0])
        return row


def _procedure_payload(procedure: ProcedureSpec) -> dict[str, object]:
    return {
        "procedure_id": procedure.procedure_id,
        "branch_scope": procedure.branch_scope,
        "name": procedure.name,
        "version": procedure.version,
        "trigger_conditions": procedure.trigger_conditions,
        "input_schema": procedure.input_schema,
        "output_schema": procedure.output_schema,
        "implementation_ref": procedure.implementation_ref,
        "preconditions": procedure.preconditions,
        "known_failures": procedure.known_failures,
        "source_evidence_refs": procedure.source_evidence_refs,
        "rollback_ref": procedure.rollback_ref,
        "authority_effect": AUTHORITY_EFFECT,
        "promotion_state": PROMOTION_STATE,
    }


def _evaluation_payload(report: EvaluationReport) -> dict[str, object]:
    return {
        "procedure_id": report.procedure_id,
        "results": [
            {
                "fixture_id": result.fixture_id,
                "tier": result.tier.value,
                "passed": result.passed,
                "actual": result.actual,
                "expected": result.expected,
            }
            for result in report.results
        ],
        "canary_required": report.canary_required,
        "authority_effect": report.authority_effect,
        "promotion_state": report.promotion_state,
    }


def _capability_payload(capability: CapabilityRecord) -> dict[str, object]:
    return {
        "capability_id": capability.capability_id,
        "branch_scope": capability.branch_scope,
        "description": capability.description,
        "procedure_ids": capability.procedure_ids,
        "known_tasks": capability.known_tasks,
        "known_failure_modes": capability.known_failure_modes,
        "maturity_stage": capability.maturity_stage.value,
        "recent_eval_profile": capability.recent_eval_profile,
        "transfer_fixture_ids": capability.transfer_fixture_ids,
        "authority_effect": capability.authority_effect,
        "promotion_state": capability.promotion_state,
    }


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
