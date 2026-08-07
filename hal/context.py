#!/usr/bin/env python3
"""Read-only Context Pack Status view for mq-hal.

This command reports whether the mqobsidian context-compression layer is
present and healthy. It never generates context packs (that belongs to
mq-agent) and never writes to mqobsidian. It only reads the local scaffold,
the token-budget script, the context-pack schema, and the latest generated
task pack, then summarizes readiness for the operator.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from hal.feedback import render_feedback, surface_feedback
except ModuleNotFoundError:  # direct script execution outside the repo root
    from feedback import (  # type: ignore[no-redef, import-not-found]
        render_feedback,
        surface_feedback,
    )

STATUS_SCHEMA = "mq_hal.context_status.v1"

# Files that make up the mqobsidian context-compression scaffold.
# Keys are stable JSON check names; values are paths relative to the
# mqobsidian root.
SCAFFOLD: dict[str, str] = {
    "context_budget_doc": "docs/context-budget.md",
    "roadmap_doc": "docs/roadmap-token-reduction.md",
    "context_pack_schema": "schemas/context-pack.v1.json",
    "context_pack_template": "templates/context-pack.md",
    "sanitized_example": "examples/sanitized-context-pack.md",
    "token_budget_script": "scripts/check-token-budget.py",
}

TASK_PACK = ".mq/context/task-pack.md"
BUDGET_SCRIPT = "scripts/check-token-budget.py"
BUDGET_COMMAND = "python3 scripts/check-token-budget.py"

# Human labels for the text view, in display order.
LABELS: list[tuple[str, str]] = [
    ("repo_found", "mqobsidian"),
    ("context_budget_doc", "context budget docs"),
    ("roadmap_doc", "roadmap docs"),
    ("context_pack_schema", "context-pack schema"),
    ("context_pack_template", "context-pack template"),
    ("sanitized_example", "sanitized example"),
    ("token_budget_script", "token budget script"),
    ("latest_task_pack", "latest task-pack"),
]

SAMPLE: dict[str, Any] = {
    "schema": STATUS_SCHEMA,
    "mqobsidian_path": "~/mqobsidian",
    "status": "PASS",
    "checks": {
        "repo_found": True,
        "context_budget_doc": True,
        "roadmap_doc": True,
        "context_pack_schema": True,
        "context_pack_template": True,
        "sanitized_example": True,
        "token_budget_script": True,
        "latest_task_pack": True,
    },
    "latest_task_pack": ".mq/context/task-pack.md",
    "target_readiness": "codex",
    "token_budget": {
        "status": "PASS",
        "command": BUDGET_COMMAND,
        "ran": True,
    },
    "recommendation": "Context layer is ready. mq-agent can generate packs and Codex/Claude can read them.",
    "collected_at": "2026-06-17T00:00:00+00:00",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_root(override: str | None = None) -> Path:
    """Resolve the mqobsidian root.

    Resolution order: explicit --root, then MQOBSIDIAN_PATH, then ~/mqobsidian.
    """
    if override:
        return Path(override).expanduser()
    env = os.environ.get("MQOBSIDIAN_PATH")
    if env:
        return Path(env).expanduser()
    return Path.home() / "mqobsidian"


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_target(task_pack: Path) -> str | None:
    """Read the `target:` frontmatter value from a context pack, if present."""
    if not task_pack.exists():
        return None
    try:
        text = task_pack.read_text(encoding="utf-8")
    except OSError:
        return None
    in_frontmatter = False
    for index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if index == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            break
        if in_frontmatter and stripped.startswith("target:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def run_token_budget(root: Path, run: bool) -> dict[str, Any]:
    """Delegate to mqobsidian's check-token-budget.py. Never raises.

    Returns a deterministic dict. Status is UNKNOWN when the script is absent
    or the check was not run; PASS on exit 0; FAIL otherwise.
    """
    script = root / BUDGET_SCRIPT
    payload: dict[str, Any] = {"status": "UNKNOWN", "command": BUDGET_COMMAND, "ran": False}
    if not script.exists():
        payload["detail"] = "token budget script not found"
        return payload
    if not run:
        payload["detail"] = "not checked (run: mq-hal context budget)"
        return payload
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        payload["detail"] = f"token budget check could not run: {exc}"
        return payload
    output = (result.stdout or result.stderr or "").strip()
    payload.update(
        {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "ran": True,
            "returncode": int(result.returncode),
            "detail": output.splitlines()[-1] if output else "",
        }
    )
    return payload


def compute_status(checks: dict[str, bool], budget: dict[str, Any]) -> str:
    if not checks.get("repo_found"):
        return "WARN"
    if budget.get("status") == "FAIL":
        return "FAIL"
    scaffold_complete = all(checks[key] for key in SCAFFOLD)
    if not scaffold_complete:
        return "WARN"
    if not checks.get("latest_task_pack"):
        return "WARN"
    return "PASS"


def recommend(status: str, checks: dict[str, bool], budget: dict[str, Any]) -> str:
    if not checks.get("repo_found"):
        return (
            "mqobsidian not found. Set MQOBSIDIAN_PATH or clone the vault to "
            "~/mqobsidian to enable the context-compression layer."
        )
    missing = [SCAFFOLD[key] for key in SCAFFOLD if not checks[key]]
    if missing:
        return "mqobsidian context scaffold incomplete; missing: " + ", ".join(missing) + "."
    if budget.get("status") == "FAIL":
        return "Token budget check failed in mqobsidian. Run `mq-hal context budget` for details."
    if not checks.get("latest_task_pack"):
        return (
            "Scaffold present but no task pack yet. Ask mq-agent to generate "
            "one into .mq/context/task-pack.md."
        )
    return "Context layer is ready. mq-agent can generate packs and Codex/Claude can read them."


def collect(root: Path, run_budget: bool = True) -> dict[str, Any]:
    repo_found = root.exists() and root.is_dir()

    checks: dict[str, bool] = {"repo_found": repo_found}
    for key, rel_path in SCAFFOLD.items():
        checks[key] = (root / rel_path).exists() if repo_found else False

    task_pack_path = root / TASK_PACK
    latest_present = task_pack_path.exists() if repo_found else False
    checks["latest_task_pack"] = latest_present

    budget = run_token_budget(root, run=run_budget and repo_found)
    status = compute_status(checks, budget)

    return surface_feedback({
        "schema": STATUS_SCHEMA,
        "mqobsidian_path": str(root),
        "status": status,
        "checks": checks,
        "latest_task_pack": rel(task_pack_path, root) if latest_present else None,
        "target_readiness": read_target(task_pack_path) if latest_present else None,
        "token_budget": budget,
        "recommendation": recommend(status, checks, budget),
        "collected_at": now_iso(),
    }, surface="Context", command="mq-hal context status")


def found(flag: bool) -> str:
    return "found" if flag else "missing"


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def render_status(data: dict[str, Any]) -> None:
    print("Context Pack Status")
    print("===================")
    print()
    checks = data["checks"]
    for key, label in LABELS:
        print(f"  {label + ':':<22} {found(bool(checks.get(key)))}")
    budget = data["token_budget"]
    print(f"  {'token budget:':<22} {str(budget.get('status', 'UNKNOWN')).lower()}")
    print(f"  {'target readiness:':<22} {data.get('target_readiness') or '-'}")
    print()
    print(f"Overall: {data['status']}")
    print(f"Path:    {data['mqobsidian_path']}")
    print(f"Hint:    {data['recommendation']}")


def render_latest_pack(data: dict[str, Any]) -> None:
    print("Latest Task Pack")
    print("================")
    print()
    pack = data.get("latest_task_pack")
    if not pack:
        print("latest task-pack: missing")
        print()
        print(data["recommendation"])
        return
    print(f"path:   {pack}")
    print(f"target: {data.get('target_readiness') or '-'}")
    print(f"root:   {data['mqobsidian_path']}")


def render_budget(data: dict[str, Any]) -> None:
    budget = data["token_budget"]
    print("Context Token Budget")
    print("====================")
    print()
    print(f"status:  {str(budget.get('status', 'UNKNOWN')).lower()}")
    print(f"command: {budget.get('command')}")
    if budget.get("detail"):
        print(f"detail:  {budget['detail']}")


def context_open(root: Path, note: str | None) -> dict[str, Any]:
    """Resolve a file strictly inside the mqobsidian root and preview it.

    Read-only. Refuses any path that escapes the root.
    """
    target_rel = note or TASK_PACK
    resolved_root = root.resolve()
    candidate = (root / target_rel).resolve()
    operation = "context_open"

    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return {
            "operation": operation,
            "status": "rejected",
            "root": str(resolved_root),
            "path": str(candidate),
            "returncode": 2,
            "error": "refused: target is outside the mqobsidian root.",
        }

    if not candidate.exists():
        return {
            "operation": operation,
            "status": "missing",
            "root": str(resolved_root),
            "path": rel(candidate, resolved_root),
            "returncode": 1,
            "error": "file not found inside mqobsidian.",
        }

    try:
        text = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "operation": operation,
            "status": "error",
            "root": str(resolved_root),
            "path": rel(candidate, resolved_root),
            "returncode": 1,
            "error": str(exc),
        }

    preview = "\n".join(text.splitlines()[:40])
    return {
        "operation": operation,
        "status": "ok",
        "root": str(resolved_root),
        "path": rel(candidate, resolved_root),
        "preview": preview,
        "returncode": 0,
    }


def render_open(result: dict[str, Any]) -> None:
    print("Context Open")
    print("============")
    print()
    print(f"path:   {result.get('path', '-')}")
    print(f"status: {result.get('status', '-')}")
    if result.get("error"):
        print()
        print(result["error"])
        return
    preview = result.get("preview")
    if preview:
        print()
        print(preview)


COMMANDS = ("status", "latest-pack", "budget", "open")

USAGE = (
    "usage: mq-hal context [status|latest-pack|budget|open [PATH]] "
    "[--json] [--sample] [--root ROOT] [--no-budget]\n\n"
    "Read-only Context Pack Status for the mqobsidian token-reduction layer."
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Two-phase parse so global flags work in any position.

    argparse subparsers reset a parent option that appears before the
    subcommand, so flags are extracted first and the subcommand is taken from
    the leftover positionals.
    """
    flags = argparse.ArgumentParser(prog="mq-hal context", add_help=False)
    flags.add_argument("--json", action="store_true", help="JSON output")
    flags.add_argument("--sample", action="store_true", help="Use sample data")
    flags.add_argument("--root", help="Override mqobsidian root")
    flags.add_argument("--no-budget", action="store_true", help="Skip the token-budget check")
    flags.add_argument("-h", "--help", action="store_true")

    ns, rest = flags.parse_known_args(argv)
    strays = [item for item in rest if item.startswith("-")]
    positionals = [item for item in rest if not item.startswith("-")]
    if strays:
        flags.error("unrecognized arguments: " + " ".join(strays))

    ns.command = None
    ns.note = None
    if positionals:
        command = positionals[0]
        if command not in COMMANDS:
            flags.error(f"unknown subcommand: {command!r}")
        ns.command = command
        if command == "open" and len(positionals) > 1:
            ns.note = positionals[1]
    return ns


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.help:
        print(USAGE)
        return 0
    root = resolve_root(args.root)

    if args.command == "open":
        if args.sample:
            payload = {
                "operation": "context_open",
                "status": "ok",
                "root": "~/mqobsidian",
                "path": TASK_PACK,
                "preview": "---\nschema: context-pack.v1\ntarget: codex\n---",
                "returncode": 0,
            }
        else:
            payload = context_open(root, args.note)
        if args.json:
            print_json(payload)
        else:
            render_open(payload)
        return 0 if payload.get("returncode", 1) == 0 else int(payload["returncode"])

    if args.sample:
        data = surface_feedback(
            dict(SAMPLE), surface="Context", command="mq-hal context status"
        )
    else:
        # `budget` always runs the check; `status`/`latest-pack`/default honour --no-budget.
        run_budget = args.command == "budget" or not args.no_budget
        data = collect(root, run_budget=run_budget)

    if args.json:
        print_json(data)
        return 0

    if args.command == "latest-pack":
        render_latest_pack(data)
    elif args.command == "budget":
        render_budget(data)
    else:
        render_status(data)
    print()
    render_feedback(data["feedback"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
