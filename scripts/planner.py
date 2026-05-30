#!/usr/bin/env python3
"""mq-hal plan: generate a structured local plan for a goal."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from model_profiles import model_for_profile

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"
PLANNER_PROMPT_PATH = BASE_DIR / "prompts" / "planner.txt"
STATE_DIR = Path(
    os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
).expanduser()
STATE_PATH = STATE_DIR / "state.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "affected_repos": {
            "type": "array",
            "items": {"type": "string"},
        },
        "affected_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risk": {
            "type": "string",
            "enum": ["low", "medium", "high", "unknown"],
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "description": {"type": "string"},
                    "safe_command": {"type": ["string", "null"]},
                    "requires_confirm": {"type": "boolean"},
                },
                "required": ["id", "description", "requires_confirm"],
            },
        },
        "validation": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rollback_plan": {"type": ["string", "null"]},
    },
    "required": [
        "goal", "affected_repos", "affected_files", "risk",
        "steps", "validation", "rollback_plan",
    ],
    "additionalProperties": False,
}

SAMPLE_PLAN: dict[str, Any] = {
    "goal": "Fix release-check in macos-scripts",
    "affected_repos": ["macos-scripts"],
    "affected_files": ["scripts/release-check.sh"],
    "risk": "low",
    "steps": [
        {
            "id": 1,
            "description": "Review current release-check.sh",
            "safe_command": "cat scripts/release-check.sh",
            "requires_confirm": False,
        },
        {
            "id": 2,
            "description": "Run release-check to see current failures",
            "safe_command": "bash scripts/release-check.sh",
            "requires_confirm": False,
        },
        {
            "id": 3,
            "description": "Apply the identified fix",
            "safe_command": None,
            "requires_confirm": True,
        },
    ],
    "validation": [
        "bash scripts/release-check.sh passes without errors",
        "CI is green after the change",
    ],
    "rollback_plan": "git restore scripts/release-check.sh",
}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {"default_repo": "macos-scripts", "repos": {}}


def active_repo(config: dict[str, Any]) -> str:
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(state, dict) and state.get("active_repo"):
                return str(state["active_repo"])
        except (OSError, json.JSONDecodeError):
            pass
    return str(config.get("default_repo", ""))


def call_ollama(goal: str, config: dict[str, Any], model: str = OLLAMA_MODEL) -> str | None:
    system = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
    context = {
        "active_repo": active_repo(config),
        "configured_repos": sorted(config.get("repos", {}).keys()),
        "goal": goal,
    }
    prompt = (
        "Context JSON:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "Goal:\n"
        f"{goal}"
    )
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "format": PLAN_SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(
            f"WARN: could not reach Ollama ({exc}). "
            f"Start Ollama: ollama pull {model}",
            file=sys.stderr,
        )
        return None
    except json.JSONDecodeError as exc:
        print(f"ERROR: Ollama returned invalid JSON: {exc}", file=sys.stderr)
        return None
    text = body.get("response", "")
    return text.strip() if isinstance(text, str) and text.strip() else None


def parse_plan(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None

    required = (
        "goal", "affected_repos", "affected_files", "risk",
        "steps", "validation", "rollback_plan",
    )
    if any(key not in parsed for key in required):
        return None
    if not isinstance(parsed.get("affected_repos"), list):
        return None
    if not isinstance(parsed.get("affected_files"), list):
        return None
    if not isinstance(parsed.get("steps"), list):
        return None
    if not isinstance(parsed.get("validation"), list):
        return None

    plan: dict[str, Any] = {
        "goal": str(parsed.get("goal", "")),
        "affected_repos": [
            str(r) for r in parsed.get("affected_repos", [])
            if isinstance(r, str)
        ],
        "affected_files": [
            str(f) for f in parsed.get("affected_files", [])
            if isinstance(f, str)
        ],
        "risk": str(parsed.get("risk", "unknown"))
            if parsed.get("risk") in ("low", "medium", "high", "unknown")
            else "unknown",
        "steps": [],
        "validation": [
            str(v) for v in parsed.get("validation", [])
            if isinstance(v, str)
        ],
        "rollback_plan": (
            str(parsed["rollback_plan"])
            if isinstance(parsed.get("rollback_plan"), str)
            else None
        ),
    }
    for step in parsed.get("steps", []):
        if not isinstance(step, dict):
            return None
        step_id = step.get("id", len(plan["steps"]) + 1)
        if not isinstance(step_id, int):
            return None
        description = step.get("description")
        if not isinstance(description, str) or not description.strip():
            return None
        if "requires_confirm" not in step or not isinstance(step["requires_confirm"], bool):
            return None
        safe_command = step.get("safe_command")
        if safe_command is not None and not isinstance(safe_command, str):
            return None
        plan["steps"].append({
            "id": step_id,
            "description": description,
            "safe_command": safe_command,
            "requires_confirm": step["requires_confirm"],
        })
    return plan


def stub_plan(goal: str) -> dict[str, Any]:
    return {
        "goal": goal,
        "affected_repos": [],
        "affected_files": [],
        "risk": "unknown",
        "steps": [],
        "validation": ["Review the goal and build a plan manually."],
        "rollback_plan": None,
    }


def render(plan: dict[str, Any], out_path: Path | None = None) -> None:
    print("HAL Plan")
    print("========")
    print()
    print(f"Goal:  {plan['goal']}")
    print(f"Risk:  {plan['risk']}")
    print()

    repos = plan.get("affected_repos", [])
    if repos:
        print("Affected repos")
        print("--------------")
        for r in repos:
            print(f"  {r}")
        print()

    files = plan.get("affected_files", [])
    if files:
        print("Affected files")
        print("--------------")
        for f in files:
            print(f"  {f}")
        print()

    steps = plan.get("steps", [])
    if steps:
        print("Steps")
        print("-----")
        for step in steps:
            confirm_flag = "  ⚠ requires confirmation" if step.get(
                "requires_confirm"
            ) else ""
            print(f"{step['id']}. {step['description']}{confirm_flag}")
            if step.get("safe_command"):
                print(f"   $ {step['safe_command']}")
        print()

    validation = plan.get("validation", [])
    if validation:
        print("Validation")
        print("----------")
        for v in validation:
            print(f"  - {v}")
        print()

    rollback = plan.get("rollback_plan")
    if rollback:
        print("Rollback")
        print("--------")
        print(f"  {rollback}")
        print()

    if out_path:
        print(f"Saved: {out_path}")
        print()
        print(
            f"Review:  mq-hal critic {out_path}\n"
            f"Execute: mq-hal execute {out_path} --confirm"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal plan",
        description="Generate a structured local plan for a goal.",
    )
    parser.add_argument("goal", nargs="*", help="Goal to plan for")
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--out", metavar="FILE",
        help="Save plan to a JSON file",
    )
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Return a stub plan without calling Ollama",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Print sample plan output without calling Ollama",
    )
    parser.add_argument(
        "--model",
        help="Model profile from config/models.json",
    )
    args = parser.parse_args(argv)

    goal = " ".join(args.goal).strip()

    if args.sample:
        plan: dict[str, Any] = SAMPLE_PLAN
    elif args.no_ai or not goal:
        if not goal:
            parser.print_help()
            return 0
        plan = stub_plan(goal)
        print(
            "INFO: --no-ai mode — returning stub plan. "
            "Run without --no-ai to generate with Ollama.",
            file=sys.stderr,
        )
    else:
        config = load_config()
        try:
            model, _profile = model_for_profile(
                args.model,
                default_profile="planner",
                env_default=DEFAULT_OLLAMA_MODEL,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        raw = call_ollama(goal, config, model=model)
        if raw is None:
            plan = stub_plan(goal)
            print(
                "WARN: Ollama unavailable — returning stub plan.",
                file=sys.stderr,
            )
        else:
            parsed = parse_plan(raw)
            if parsed is None:
                print(
                    "ERROR: could not parse plan from model output.",
                    file=sys.stderr,
                )
                return 1
            plan = parsed

    out_path: Path | None = None
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if args.json_out:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    render(plan, out_path=out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
