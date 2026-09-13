#!/usr/bin/env python3
"""Inspect the repository-local RepoHarvester DevOS developer task queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TASK_FILE = ROOT / "devos" / "tasks.jsonl"
TASK_EVENT_FILE = ROOT / "devos" / "task-events.jsonl"
PROJECT_FILE = ROOT / "devos" / "project.json"


ALLOWED_EVENT_STATUS = {
    "READY",
    "BLOCKED",
    "TRACKING",
    "CLAIMED",
    "IN_PROGRESS",
    "VERIFY",
    "DONE",
    "PAUSED",
    "REJECTED",
}


def _load_jsonl(path: Path, *, label: str) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on {label} line {line_no}: {exc}") from exc
        rows.append(row)
    return rows


def load_task_declarations(path: Path = TASK_FILE) -> list[dict]:
    return _load_jsonl(path, label="task")


def load_task_events(path: Path = TASK_EVENT_FILE) -> list[dict]:
    events = _load_jsonl(path, label="task event")
    seen: set[str] = set()
    for line_no, event in enumerate(events, 1):
        required = {"event_id", "task_id", "status", "occurred_on"}
        missing = sorted(required - set(event))
        if missing:
            raise ValueError(f"task event line {line_no} missing fields: {', '.join(missing)}")
        event_id = event["event_id"]
        if not isinstance(event_id, str) or not event_id:
            raise ValueError(f"task event line {line_no} has invalid event_id")
        if event_id in seen:
            raise ValueError(f"duplicate task event id: {event_id}")
        seen.add(event_id)
        if event["status"] not in ALLOWED_EVENT_STATUS:
            raise ValueError(f"{event_id}: invalid status {event['status']}")
        for field in ("tracking_add", "evidence_refs_add"):
            values = event.get(field, [])
            if not isinstance(values, list) or not all(isinstance(item, str) and item for item in values):
                raise ValueError(f"{event_id}: {field} must be a list of non-empty strings")
    return events


def fold_task_events(tasks: list[dict], events: list[dict]) -> list[dict]:
    effective = {task["task_id"]: dict(task) for task in tasks}
    for task_id, task in effective.items():
        task["tracking"] = list(task.get("tracking", []))
        task["evidence_refs"] = list(task.get("evidence_refs", []))

    for event in events:
        task_id = event["task_id"]
        if task_id not in effective:
            raise ValueError(f"{event['event_id']}: unknown task_id {task_id}")
        task = effective[task_id]
        task["status"] = event["status"]
        if "assigned_agent" in event:
            task["assigned_agent"] = event["assigned_agent"]
        for field, event_field in (("tracking", "tracking_add"), ("evidence_refs", "evidence_refs_add")):
            for value in event.get(event_field, []):
                if value not in task[field]:
                    task[field].append(value)
        task["latest_lifecycle_event"] = event["event_id"]
        task["lifecycle_occurred_on"] = event["occurred_on"]
    return [effective[task["task_id"]] for task in tasks]


def load_tasks(path: Path = TASK_FILE, event_path: Path | None = TASK_EVENT_FILE) -> list[dict]:
    tasks = load_task_declarations(path)
    if event_path is None:
        return tasks
    return fold_task_events(tasks, load_task_events(event_path))


def load_delivery(path: Path = PROJECT_FILE) -> dict:
    project = json.loads(path.read_text(encoding="utf-8"))
    delivery = project.get("delivery") or {}
    if delivery.get("primary_runtime_target") != "browser":
        raise ValueError("RepoHarvester primary runtime target must be browser")
    if not delivery.get("contract"):
        raise ValueError("browser delivery contract is required")
    return delivery


def task_index(tasks: Iterable[dict]) -> dict[str, dict]:
    return {task["task_id"]: task for task in tasks}


def dependencies_done(task: dict, index: dict[str, dict]) -> bool:
    return all(index[dep]["status"] == "DONE" for dep in task.get("depends_on", []))


def assignable(tasks: list[dict]) -> list[dict]:
    index = task_index(tasks)
    ready = [
        task
        for task in tasks
        if task["status"] == "READY"
        and task.get("assigned_agent") is None
        and dependencies_done(task, index)
    ]
    return sorted(ready, key=lambda task: (task["priority"], task["task_id"]))


def render_task(task: dict, delivery: dict) -> str:
    deps = ",".join(task["depends_on"]) if task["depends_on"] else "none"
    branches = ",".join(task["branch_keys"])
    assignee = task["assigned_agent"] or "unassigned"
    canary = "yes" if task["transfer_canary"] else "no"
    lifecycle = task.get("latest_lifecycle_event", "declaration")
    return (
        f"{task['task_id']}  P{task['priority']}  {task['status']}  {task['title']}\n"
        f"  branches={branches} assignee={assignee} depends_on={deps} transfer_canary={canary}\n"
        f"  lifecycle={lifecycle}\n"
        f"  delivery={delivery['primary_runtime_target']} contract={delivery['contract']}\n"
        f"  objective={task['objective']}"
    )


def task_with_delivery(task: dict, delivery: dict) -> dict:
    enriched = dict(task)
    enriched["delivery_constraint"] = {
        "primary_runtime_target": delivery["primary_runtime_target"],
        "browser_class": delivery.get("browser_class"),
        "contract": delivery["contract"],
    }
    return enriched


def cmd_list(tasks: list[dict], delivery: dict, status: str | None, canary_only: bool) -> int:
    selected = tasks
    if status:
        selected = [task for task in selected if task["status"] == status]
    if canary_only:
        selected = [task for task in selected if task["transfer_canary"]]
    for task in sorted(selected, key=lambda row: (row["priority"], row["task_id"])):
        print(render_task(task, delivery))
    return 0


def cmd_next(tasks: list[dict], delivery: dict, canary_only: bool) -> int:
    candidates = assignable(tasks)
    if canary_only:
        candidates = [task for task in candidates if task["transfer_canary"]]
    if not candidates:
        print("NO_ASSIGNABLE_TASK")
        return 1
    print(render_task(candidates[0], delivery))
    return 0


def cmd_show(tasks: list[dict], delivery: dict, task_id: str) -> int:
    index = task_index(tasks)
    task = index.get(task_id)
    if task is None:
        print(f"UNKNOWN_TASK {task_id}")
        return 1
    print(json.dumps(task_with_delivery(task, delivery), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list queue entries")
    list_parser.add_argument("--status")
    list_parser.add_argument("--canary", action="store_true")

    next_parser = sub.add_parser("next", help="show highest-priority assignable task")
    next_parser.add_argument("--canary", action="store_true")

    show_parser = sub.add_parser("show", help="show one task as JSON")
    show_parser.add_argument("task_id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tasks = load_tasks()
    delivery = load_delivery()
    if args.command == "list":
        return cmd_list(tasks, delivery, args.status, args.canary)
    if args.command == "next":
        return cmd_next(tasks, delivery, args.canary)
    if args.command == "show":
        return cmd_show(tasks, delivery, args.task_id)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
