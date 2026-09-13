#!/usr/bin/env python3
"""Run one CI gate quietly and emit an actionable failure packet when it fails."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / ".build" / "ci"
FAILURE_SCHEMA = "repoharvester-ci-failure/v1"
SIGNAL_NORMALIZATION_VERSION = "repoharvester-ci-signal/v1"


def gate_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "gate"


def escape_workflow_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def failure_excerpt(output: str, limit: int = 40) -> str:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def normalized_signal(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    candidates = [
        line
        for line in reversed(lines)
        if any(
            token in line.lower()
            for token in (
                "error",
                "failed",
                "failure",
                "traceback",
                "exception",
                "assert",
            )
        )
    ]
    signal = candidates[0] if candidates else (lines[-1] if lines else "no-output")
    signal = re.sub(r"0x[0-9a-fA-F]+", "0x…", signal)
    signal = re.sub(r"\b\d+(?:\.\d+)?s\b", "<duration>", signal)
    return signal[:500]


def failure_signature(gate: str, command: str, output: str) -> str:
    payload = "\0".join((gate, command, normalized_signal(output)))
    return "ci-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def github_metadata() -> dict[str, str | None]:
    names = (
        "GITHUB_REPOSITORY",
        "GITHUB_SHA",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_WORKFLOW",
        "GITHUB_JOB",
        "GITHUB_EVENT_NAME",
        "GITHUB_REF",
        "GITHUB_HEAD_REF",
        "GITHUB_BASE_REF",
        "RUNNER_OS",
        "RUNNER_ARCH",
    )
    return {name.lower(): os.environ.get(name) for name in names}


def github_event_payload() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def ci_subject(metadata: dict[str, str | None]) -> dict[str, str | None]:
    """Describe both the tested revision and the source change revision.

    On pull_request, GITHUB_SHA is the synthetic merge commit tested by CI, not
    the PR head commit. Preserve both identities so later evidence cannot treat
    a merge-simulation result as if it tested the head commit in isolation.
    """

    event_name = metadata.get("github_event_name")
    tested_sha = metadata.get("github_sha")
    change_head_sha = tested_sha
    base_sha: str | None = None
    subject_kind = "COMMIT"
    identity_state = "COMPLETE" if tested_sha else "INCOMPLETE"

    if event_name in {"pull_request", "pull_request_target"}:
        change_head_sha = None
        payload = github_event_payload()
        pull_request = payload.get("pull_request")
        if isinstance(pull_request, dict):
            head = pull_request.get("head")
            base = pull_request.get("base")
            if isinstance(head, dict) and isinstance(head.get("sha"), str):
                change_head_sha = head["sha"]
            if isinstance(base, dict) and isinstance(base.get("sha"), str):
                base_sha = base["sha"]
        subject_kind = (
            "PULL_REQUEST_MERGE"
            if event_name == "pull_request"
            else "PULL_REQUEST_TARGET"
        )
        identity_state = "COMPLETE" if tested_sha and change_head_sha else "INCOMPLETE"

    return {
        "kind": subject_kind,
        "identity_state": identity_state,
        "tested_sha": tested_sha,
        "change_head_sha": change_head_sha,
        "base_sha": base_sha,
        "ref": metadata.get("github_ref"),
        "head_ref": metadata.get("github_head_ref"),
        "base_ref": metadata.get("github_base_ref"),
    }


def append_failure_summary(
    summary_path: Path,
    *,
    gate: str,
    command: str,
    exit_code: int,
    signature: str,
    log_path: Path,
    excerpt: str,
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write(f"## CI failure: {gate}\n\n")
        handle.write(f"- **Exit code:** `{exit_code}`\n")
        handle.write(f"- **Signature:** `{signature}`\n")
        handle.write(f"- **Full log:** `{log_path.as_posix()}`\n")
        handle.write("- **Reproduce locally:**\n\n")
        handle.write("```bash\n")
        handle.write(command + "\n")
        handle.write("```\n\n")
        handle.write("### Failure excerpt\n\n")
        handle.write("```text\n")
        handle.write((excerpt or "<no output captured>") + "\n")
        handle.write("```\n")


def run_gate(
    gate: str,
    command_args: list[str],
    *,
    log_dir: Path = DEFAULT_LOG_DIR,
) -> int:
    if not command_args:
        raise ValueError("a command is required after --")

    log_dir.mkdir(parents=True, exist_ok=True)
    slug = gate_slug(gate)
    log_path = log_dir / f"{slug}.log"
    packet_path = log_dir / f"{slug}.failure.json"
    command = shlex.join(command_args)

    started = time.monotonic()
    completed = subprocess.run(
        command_args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    elapsed = time.monotonic() - started
    output = completed.stdout or ""
    log_path.write_text(output, encoding="utf-8")

    if completed.returncode == 0:
        print(f"PASS {gate} ({elapsed:.2f}s)")
        return 0

    excerpt = failure_excerpt(output)
    signal = normalized_signal(output)
    signature = failure_signature(gate, command, output)
    metadata = github_metadata()
    run_id = metadata.get("github_run_id") or "local"
    job = metadata.get("github_job") or "local"
    packet = {
        "schema": FAILURE_SCHEMA,
        "status": "FAILED",
        "gate": gate,
        "command": command,
        "exit_code": completed.returncode,
        "signature": signature,
        "signal_normalization_version": SIGNAL_NORMALIZATION_VERSION,
        "normalized_signal": signal,
        "observation_root": f"github-actions:{run_id}:{job}:{slug}",
        "subject": ci_subject(metadata),
        "log_path": log_path.relative_to(ROOT).as_posix(),
        "excerpt": excerpt,
        "metadata": metadata,
        "authority_effect": "NONE",
    }
    packet_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        append_failure_summary(
            Path(summary),
            gate=gate,
            command=command,
            exit_code=completed.returncode,
            signature=signature,
            log_path=log_path.relative_to(ROOT),
            excerpt=excerpt,
        )

    annotation = (
        f"{gate} failed with exit {completed.returncode}; "
        f"signature {signature}; reproduce: {command}"
    )
    print(
        f"::error title={escape_workflow_data('CI gate failed: ' + gate)}::"
        f"{escape_workflow_data(annotation)}"
    )
    print(f"FAIL {gate} | {signature} | log={log_path.relative_to(ROOT)}", file=sys.stderr)
    if excerpt:
        print(excerpt, file=sys.stderr)

    return completed.returncode if 0 < completed.returncode < 256 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_gate(args.gate, args.command, log_dir=args.log_dir)
    except (OSError, ValueError) as exc:
        print(f"ci goblin reporter failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
