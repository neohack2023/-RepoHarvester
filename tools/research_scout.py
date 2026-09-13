#!/usr/bin/env python3
"""Plan and validate bounded autonomous research for RepoHarvester DevOS."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEVOS = ROOT / "devos"
POLICY_FILE = DEVOS / "research-policy.json"
PROJECT_FILE = DEVOS / "project.json"
TASK_FILE = DEVOS / "tasks.jsonl"
BRANCH_FILE = DEVOS / "branches.jsonl"
OPPORTUNITY_FILE = DEVOS / "opportunities.jsonl"

AUTHORITY_EFFECT = "NONE"
PROMOTION_STATE = "CANDIDATE_ONLY"

RECEIPT_FIELDS = {
    "research_id",
    "trigger_task_ids",
    "branch_keys",
    "trigger_signals",
    "questions",
    "queries",
    "sources",
    "claims",
    "uncertainties",
    "inspirations",
    "opportunities",
    "no_op_reason",
    "authority_effect",
    "promotion_state",
}

OPPORTUNITY_FIELDS = {
    "opportunity_id",
    "title",
    "status",
    "branch_keys",
    "trigger_task_ids",
    "need",
    "proposal",
    "source_refs",
    "evidence_refs",
    "expected_value",
    "novelty_reason",
    "project_fit",
    "risks",
    "validation_plan",
    "cross_reference_disposition",
    "suggested_disposition",
    "authority_effect",
    "promotion_state",
}

ALLOWED_OPPORTUNITY_STATUS = {
    "CANDIDATE",
    "PARKED",
    "REJECTED",
    "PROMOTED_TO_TASK",
    "PROMOTED_TO_INCUBATION",
}
ALLOWED_CROSS_REFERENCE = {
    "NEW",
    "SUPPORTS_EXISTING",
    "OVERLAPS_EXISTING",
    "CONTRADICTS_EXISTING",
    "SUPERSEDED",
    "INSUFFICIENT",
}
ALLOWED_DISPOSITION = {
    "NO_OP",
    "PARK",
    "RESEARCH_MORE",
    "PROPOSE_TASK",
    "PROPOSE_FEATURE_INCUBATION",
    "PROPOSE_EXPERIMENT",
    "PROPOSE_ARCHITECTURE_COMPARISON",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON on line {line_no}: {exc}") from exc
    return rows


def by_key(rows: Iterable[dict], key: str) -> dict[str, dict]:
    return {row[key]: row for row in rows}


def normalize_signals(signals: list[str], policy: dict) -> list[str]:
    allowed = set(policy["explicit_signals"])
    unknown = sorted(set(signals) - allowed)
    if unknown:
        raise ValueError(f"unknown research signal(s): {', '.join(unknown)}")
    return sorted(set(signals))


def task_text(task: dict) -> str:
    parts = [task.get("title", ""), task.get("objective", "")]
    parts.extend(task.get("acceptance", []))
    return " ".join(parts).lower()


def stable_plan_id(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return f"research-plan:{digest}"


def research_triggers(
    *,
    task: dict | None,
    branch: dict | None,
    explicit_signals: list[str],
    policy: dict,
    project: dict,
) -> list[str]:
    triggers: set[str] = set(explicit_signals)

    if task is not None:
        if task.get("status") == "BLOCKED":
            triggers.add("blocker")
        if task.get("task_type") in policy["automatic_task_types"]:
            triggers.add(f"task-type:{task['task_type']}")
        for key in task.get("branch_keys", []):
            if key in policy["automatic_branch_keys"]:
                triggers.add(f"branch:{key}")

        delivery = project.get("delivery", {})
        if delivery.get("primary_runtime_target") == "browser":
            text = task_text(task)
            matched = sorted(
                keyword
                for keyword in policy["browser_external_keywords"]
                if keyword in text
            )
            if matched:
                triggers.add("browser-external-dependency")
                triggers.update(f"keyword:{keyword}" for keyword in matched[:5])

    if branch is not None and branch.get("branch_key") in policy["automatic_branch_keys"]:
        triggers.add(f"branch:{branch['branch_key']}")

    return sorted(triggers)


def select_lanes(triggers: list[str], task: dict | None, policy: dict) -> list[str]:
    lanes: list[str] = []

    def add(name: str) -> None:
        if name in policy["research_lanes"] and name not in lanes:
            lanes.append(name)

    if triggers:
        add("CURRENT_STATE")
        add("IMPLEMENTATIONS")
    if any(
        trigger in triggers
        for trigger in ("blocker", "capability-gap", "design-dead-end", "external-uncertainty")
    ) or "browser-external-dependency" in triggers:
        add("FAILURE_MODES")
    if (
        task is not None
        and task.get("task_type") == "feature_incubation"
        or "design-dead-end" in triggers
        or "opportunity-window" in triggers
        or "weak-comparison" in triggers
    ):
        add("ADJACENT_DESIGN")
    if triggers:
        add("OPPORTUNITY")
    return lanes


def build_questions(task: dict | None, branch: dict | None, lanes: list[str]) -> list[str]:
    subject = task["title"] if task is not None else branch["branch_key"]
    questions: list[str] = []
    if "CURRENT_STATE" in lanes:
        questions.append(
            f"What current primary-source constraints or capabilities materially affect {subject}?"
        )
    if "IMPLEMENTATIONS" in lanes:
        questions.append(
            f"Which concrete implementations or open-source systems solve problems adjacent to {subject}, and what is transferable?"
        )
    if "FAILURE_MODES" in lanes:
        questions.append(
            f"What failure modes, browser/platform limits, postmortems, or counterexamples should RepoHarvester test for in {subject}?"
        )
    if "ADJACENT_DESIGN" in lanes:
        questions.append(
            f"Which games or systems offer useful design analogies for {subject}, and where does the analogy stop applying?"
        )
    if "OPPORTUNITY" in lanes:
        questions.append(
            f"Is there a bounded feature, tool, technique, or experiment that would materially improve RepoHarvester's current need around {subject}?"
        )
    return questions


def make_plan(
    *,
    task: dict | None,
    branch: dict | None,
    signals: list[str],
    policy: dict,
    project: dict,
) -> dict:
    triggers = research_triggers(
        task=task,
        branch=branch,
        explicit_signals=signals,
        policy=policy,
        project=project,
    )
    lanes = select_lanes(triggers, task, policy)
    branch_keys = (
        list(task.get("branch_keys", []))
        if task is not None
        else [branch["branch_key"]]
    )
    trigger_task_ids = [task["task_id"]] if task is not None else []
    core = {
        "trigger_task_ids": trigger_task_ids,
        "branch_keys": branch_keys,
        "triggers": triggers,
        "lanes": lanes,
        "delivery_target": project.get("delivery", {}).get("primary_runtime_target"),
    }
    return {
        "plan_id": stable_plan_id(core),
        "research_required": bool(triggers),
        **core,
        "questions": build_questions(task, branch, lanes) if triggers else [],
        "budget": policy["default_budget"],
        "source_policy": policy["source_policy"],
        "receipt_schema": policy["research_receipt_schema"],
        "opportunity_ledger": policy["opportunity_ledger"],
        "authority_effect": AUTHORITY_EFFECT,
        "promotion_state": PROMOTION_STATE,
    }


def validate_receipt(receipt: dict, policy: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(RECEIPT_FIELDS - set(receipt))
    extra = sorted(set(receipt) - RECEIPT_FIELDS)
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"extra fields: {', '.join(extra)}")
    if errors:
        return errors

    if receipt["authority_effect"] != AUTHORITY_EFFECT:
        errors.append("authority_effect must be NONE")
    if receipt["promotion_state"] != PROMOTION_STATE:
        errors.append("promotion_state must be CANDIDATE_ONLY")
    if not str(receipt["research_id"]).startswith("REPOHARVESTER-RESEARCH-"):
        errors.append("research_id must start REPOHARVESTER-RESEARCH-")
    if not receipt["branch_keys"]:
        errors.append("branch_keys required")
    if not receipt["trigger_signals"]:
        errors.append("trigger_signals required")
    if not receipt["questions"]:
        errors.append("questions required")

    budget = policy["default_budget"]
    if len(receipt["queries"]) > budget["max_queries"]:
        errors.append("query budget exceeded")
    if len(receipt["sources"]) > budget["max_sources"]:
        errors.append("source budget exceeded")
    if len(receipt["opportunities"]) > budget["max_opportunities"]:
        errors.append("opportunity budget exceeded")

    refs: set[str] = set()
    source_classes: set[str] = set()
    for index, source in enumerate(receipt["sources"], 1):
        for field in ("source_ref", "source_class", "title", "retrieved_on"):
            if not source.get(field):
                errors.append(f"source {index}: {field} required")
        ref = source.get("source_ref")
        if ref in refs:
            errors.append(f"duplicate source_ref: {ref}")
        if ref:
            refs.add(ref)
        if source.get("source_class"):
            source_classes.add(source["source_class"])

    if receipt["sources"] and len(source_classes) < min(
        budget["min_source_classes"], len(receipt["sources"])
    ):
        errors.append("insufficient source-class diversity")

    for index, claim in enumerate(receipt["claims"], 1):
        if claim.get("fact_or_inference") not in {"FACT", "INFERENCE"}:
            errors.append(f"claim {index}: invalid fact_or_inference")
        if claim.get("confidence") not in {"LOW", "MEDIUM", "HIGH"}:
            errors.append(f"claim {index}: invalid confidence")
        missing_refs = sorted(set(claim.get("source_refs", [])) - refs)
        if missing_refs:
            errors.append(
                f"claim {index}: unknown source refs {', '.join(missing_refs)}"
            )

    for index, item in enumerate(receipt["inspirations"], 1):
        if not item.get("analogy_boundary"):
            errors.append(f"inspiration {index}: analogy_boundary required")
        missing_refs = sorted(set(item.get("source_refs", [])) - refs)
        if missing_refs:
            errors.append(
                f"inspiration {index}: unknown source refs {', '.join(missing_refs)}"
            )

    if not receipt["opportunities"] and not receipt["no_op_reason"]:
        errors.append("receipt must contain opportunities or an explicit no_op_reason")
    return errors


def validate_opportunities(
    opportunities: list[dict], tasks: list[dict], branches: list[dict]
) -> list[str]:
    errors: list[str] = []
    task_ids = {task["task_id"] for task in tasks}
    branch_keys = {branch["branch_key"] for branch in branches}
    ids: set[str] = set()

    for line_no, item in enumerate(opportunities, 1):
        missing = sorted(OPPORTUNITY_FIELDS - set(item))
        extra = sorted(set(item) - OPPORTUNITY_FIELDS)
        prefix = f"opportunity line {line_no}"
        if missing:
            errors.append(f"{prefix}: missing {', '.join(missing)}")
            continue
        if extra:
            errors.append(f"{prefix}: extra {', '.join(extra)}")
        oid = item["opportunity_id"]
        if oid in ids:
            errors.append(f"{prefix}: duplicate opportunity_id {oid}")
        ids.add(oid)
        if not oid.startswith("REPOHARVESTER-OPP-"):
            errors.append(f"{prefix}: invalid opportunity_id")
        if item["status"] not in ALLOWED_OPPORTUNITY_STATUS:
            errors.append(f"{oid}: invalid status {item['status']}")
        if item["cross_reference_disposition"] not in ALLOWED_CROSS_REFERENCE:
            errors.append(f"{oid}: invalid cross_reference_disposition")
        if item["suggested_disposition"] not in ALLOWED_DISPOSITION:
            errors.append(f"{oid}: invalid suggested_disposition")
        if item["authority_effect"] != AUTHORITY_EFFECT:
            errors.append(f"{oid}: authority_effect must be NONE")
        if item["promotion_state"] != PROMOTION_STATE:
            errors.append(f"{oid}: promotion_state must be CANDIDATE_ONLY")
        for branch_key in item["branch_keys"]:
            if branch_key not in branch_keys:
                errors.append(f"{oid}: unknown branch {branch_key}")
        for task_id in item["trigger_task_ids"]:
            if task_id not in task_ids:
                errors.append(f"{oid}: unknown trigger task {task_id}")
        for field in (
            "title",
            "need",
            "proposal",
            "expected_value",
            "novelty_reason",
            "project_fit",
        ):
            if not str(item[field]).strip():
                errors.append(f"{oid}: {field} required")
        if not item["source_refs"]:
            errors.append(f"{oid}: source_refs required")
        if not item["evidence_refs"]:
            errors.append(f"{oid}: evidence_refs required")
        if not item["validation_plan"]:
            errors.append(f"{oid}: validation_plan required")
    return errors


def render_plan(plan: dict) -> str:
    lines = [
        f"{plan['plan_id']} research_required={'yes' if plan['research_required'] else 'no'}",
        f"  tasks={','.join(plan['trigger_task_ids']) or 'none'} branches={','.join(plan['branch_keys'])}",
        f"  triggers={','.join(plan['triggers']) or 'none'}",
        f"  lanes={','.join(plan['lanes']) or 'none'}",
        f"  budget=queries:{plan['budget']['max_queries']} sources:{plan['budget']['max_sources']} opportunities:{plan['budget']['max_opportunities']}",
    ]
    for question in plan["questions"]:
        lines.append(f"  ? {question}")
    lines.append(
        f"  authority_effect={plan['authority_effect']} promotion_state={plan['promotion_state']}"
    )
    return "\n".join(lines)


def cmd_preflight(args: argparse.Namespace) -> int:
    policy = load_json(POLICY_FILE)
    project = load_json(PROJECT_FILE)
    tasks = load_jsonl(TASK_FILE)
    branches = load_jsonl(BRANCH_FILE)
    task_map = by_key(tasks, "task_id")
    branch_map = by_key(branches, "branch_key")
    signals = normalize_signals(args.signal or [], policy)

    task = None
    branch = None
    if args.task:
        task = task_map.get(args.task)
        if task is None:
            raise ValueError(f"unknown task: {args.task}")
    if args.branch:
        branch = branch_map.get(args.branch)
        if branch is None:
            raise ValueError(f"unknown branch: {args.branch}")

    plan = make_plan(
        task=task,
        branch=branch,
        signals=signals,
        policy=policy,
        project=project,
    )
    print(json.dumps(plan, indent=2, sort_keys=True) if args.json else render_plan(plan))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    policy = load_json(POLICY_FILE)
    project = load_json(PROJECT_FILE)
    tasks = load_jsonl(TASK_FILE)
    plans: list[tuple[int, str, dict]] = []
    for task in tasks:
        if task["status"] in {"DONE", "REJECTED", "PAUSED"}:
            continue
        plan = make_plan(
            task=task,
            branch=None,
            signals=[],
            policy=policy,
            project=project,
        )
        if plan["research_required"]:
            plans.append((task["priority"], task["task_id"], plan))
    plans.sort(key=lambda item: (item[0], item[1]))
    if args.json:
        print(json.dumps([plan for _, _, plan in plans], indent=2, sort_keys=True))
    else:
        for _, _, plan in plans:
            print(render_plan(plan))
    return 0


def cmd_validate_receipt(args: argparse.Namespace) -> int:
    receipt = load_json(Path(args.path))
    errors = validate_receipt(receipt, load_json(POLICY_FILE))
    if errors:
        for error in errors:
            print(f"research receipt error: {error}")
        return 1
    print(f"research receipt valid: {receipt['research_id']}")
    return 0


def cmd_validate_opportunities(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else OPPORTUNITY_FILE
    opportunities = load_jsonl(path)
    errors = validate_opportunities(
        opportunities,
        load_jsonl(TASK_FILE),
        load_jsonl(BRANCH_FILE),
    )
    if errors:
        for error in errors:
            print(f"research opportunity error: {error}")
        return 1
    print(f"research opportunities valid: {len(opportunities)}")
    return 0


def cmd_opportunities(args: argparse.Namespace) -> int:
    rows = load_jsonl(OPPORTUNITY_FILE)
    if args.status:
        rows = [row for row in rows if row["status"] == args.status]
    for row in rows:
        print(
            f"{row['opportunity_id']} {row['status']} {row['suggested_disposition']} {row['title']}\n"
            f"  need={row['need']}\n"
            f"  branches={','.join(row['branch_keys'])} tasks={','.join(row['trigger_task_ids']) or 'none'}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="decide whether bounded research is warranted")
    target = preflight.add_mutually_exclusive_group(required=True)
    target.add_argument("--task")
    target.add_argument("--branch")
    preflight.add_argument("--signal", action="append", default=[])
    preflight.add_argument("--json", action="store_true")

    scan = sub.add_parser("scan", help="show active tasks that trigger autonomous research")
    scan.add_argument("--json", action="store_true")

    receipt = sub.add_parser("validate-receipt", help="validate a completed research receipt")
    receipt.add_argument("path")

    opportunities = sub.add_parser("validate-opportunities", help="validate the opportunity ledger")
    opportunities.add_argument("path", nargs="?")

    list_opp = sub.add_parser("opportunities", help="list research opportunity candidates")
    list_opp.add_argument("--status")
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        if args.command == "preflight":
            return cmd_preflight(args)
        if args.command == "scan":
            return cmd_scan(args)
        if args.command == "validate-receipt":
            return cmd_validate_receipt(args)
        if args.command == "validate-opportunities":
            return cmd_validate_opportunities(args)
        if args.command == "opportunities":
            return cmd_opportunities(args)
        raise AssertionError(args.command)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"research scout error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
