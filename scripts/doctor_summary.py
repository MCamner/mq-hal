#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from json import JSONDecoder
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"
PROMPT_PATH = BASE_DIR / "prompts" / "doctor-summary.txt"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")

SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "key_findings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_next_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "safe_commands": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "status",
        "summary",
        "key_findings",
        "recommended_next_steps",
        "safe_commands",
    ],
    "additionalProperties": False,
}

SAMPLE_DOCTOR_JSON = {
    "summary": {
        "ok": 7,
        "warn": 1,
        "fail": 0,
    },
    "checks": [
        {"name": "git", "status": "ok", "message": "git found"},
        {"name": "brew", "status": "ok", "message": "brew found"},
        {
            "name": "repo",
            "status": "warn",
            "message": "working tree has uncommitted changes",
        },
    ],
}


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "default_repo": "macos-scripts",
            "repos": {"macos-scripts": "~/macos-scripts"},
        }

    config = load_json_file(CONFIG_PATH)

    if "repos" not in config or not isinstance(config["repos"], dict):
        die("config/repos.json must contain a repos object")

    return config


def expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def resolve_repo(repo_name: str | None) -> tuple[str, Path]:
    config = load_config()
    repos = config.get("repos", {})

    if not isinstance(repos, dict) or not repos:
        die("no repos configured in config/repos.json")

    name = repo_name or str(config.get("default_repo") or "macos-scripts")

    if name not in repos:
        known = ", ".join(sorted(str(k) for k in repos))
        die(f"unknown repo '{name}'. Known repos: {known}", 2)

    path = expand_path(str(repos[name]))

    if not path.exists():
        die(f"repo '{name}' does not exist at {path}")

    return name, path


def extract_json(text: str) -> Any:
    stripped = text.strip()

    if not stripped:
        die("doctor returned empty output")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    decoder = JSONDecoder()

    for idx, char in enumerate(stripped):
        if char not in "{[":
            continue
        try:
            parsed, _end = decoder.raw_decode(stripped[idx:])
            return parsed
        except json.JSONDecodeError:
            continue

    die("could not extract JSON from doctor output")


def doctor_commands(repo_path: Path) -> list[list[str]]:
    commands: list[list[str]] = []

    commands.append(["mqlaunch", "doctor", "--json"])

    launcher = repo_path / "terminal" / "launchers" / "mqlaunch.sh"
    if launcher.exists():
        commands.append([str(launcher), "doctor", "--json"])

    doctor = repo_path / "tools" / "scripts" / "doctor.sh"
    if doctor.exists():
        commands.append([str(doctor), "--json"])

    return commands


def run_doctor(repo_path: Path) -> tuple[Any, str, str]:
    errors: list[str] = []

    for command in doctor_commands(repo_path):
        try:
            completed = subprocess.run(
                command,
                cwd=str(repo_path),
                text=True,
                capture_output=True,
                timeout=120,
            )
        except FileNotFoundError:
            errors.append(f"command not found: {command[0]}")
            continue
        except subprocess.TimeoutExpired:
            errors.append(f"timeout: {' '.join(command)}")
            continue

        output = (completed.stdout or "") + (
            "\n" + completed.stderr if completed.stderr else ""
        )

        if completed.returncode not in (0, 1, 2):
            errors.append(
                f"command failed ({completed.returncode}): {' '.join(command)}\n{output[:1000]}"
            )
            continue

        parsed = extract_json(output)
        return parsed, output, " ".join(command)

    die("could not run doctor --json:\n" + "\n".join(errors))


def walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            items.extend(walk(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            items.extend(walk(child, child_path))
    else:
        items.append((path, value))

    return items


def deterministic_summary(data: Any) -> dict[str, Any]:
    counts: dict[str, int] = {
        "ok": 0, "pass": 0, "warn": 0, "warning": 0,
        "fail": 0, "failed": 0, "error": 0, "missing": 0,
    }
    findings: list[str] = []

    for path, value in walk(data):
        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in counts:
                counts[lower] += 1
            if any(
                token in lower
                for token in ["warn", "fail", "error", "missing", "not found", "dirty", "uncommitted"]
            ):
                findings.append(f"{path}: {value}")
        if isinstance(value, bool) and value is False:
            key = path.lower()
            if any(token in key for token in ["ok", "pass", "ready", "valid"]):
                findings.append(f"{path}: false")

    bad = counts["fail"] + counts["failed"] + counts["error"] + counts["missing"]
    warn = counts["warn"] + counts["warning"]

    if bad > 0:
        status = "Needs attention"
    elif warn > 0 or findings:
        status = "Mostly healthy, with warnings"
    else:
        status = "Healthy"

    if not findings:
        findings = ["No obvious warnings or failures detected in the doctor JSON."]

    return {
        "status": status,
        "summary": f"Detected {bad} serious issue(s) and {warn} warning(s) from doctor JSON.",
        "key_findings": findings[:8],
        "recommended_next_steps": [
            "Review the doctor JSON for exact failing checks.",
            "Fix warnings before release work.",
            "Run selftest and release-check after changes.",
        ],
        "safe_commands": [
            "mqlaunch doctor --json | jq .",
            "mqlaunch selftest",
            "mqlaunch release-check",
        ],
    }


def prompt_text() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "Summarize mqlaunch doctor JSON output. Recommend safe next steps only."


def call_ollama_summary(data: Any, repo_name: str, command: str) -> dict[str, Any] | None:
    compact_json = json.dumps(data, ensure_ascii=False, indent=2)

    if len(compact_json) > 18000:
        compact_json = compact_json[:18000] + "\n...TRUNCATED..."

    user_prompt = f"Repo: {repo_name}\nDoctor command: {command}\n\nDoctor JSON:\n{compact_json}\n"

    payload = {
        "model": OLLAMA_MODEL,
        "system": prompt_text(),
        "prompt": user_prompt,
        "format": SUMMARY_SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    raw = envelope.get("response")
    if not isinstance(raw, str) or not raw.strip():
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def render(summary: dict[str, Any], repo_name: str, repo_path: Path, command: str, used_ai: bool) -> None:
    source = "Ollama" if used_ai else "deterministic fallback"

    print("HAL Doctor Summary")
    print("==================")
    print()
    print(f"Repo:    {repo_name}")
    print(f"Path:    {repo_path}")
    print(f"Command: {command}")
    print(f"Source:  {source}")
    print()
    print(f"Status: {summary.get('status', 'Unknown')}")
    print()

    print("Summary")
    print("-------")
    print(summary.get("summary", "No summary available."))
    print()

    findings = summary.get("key_findings", [])
    if isinstance(findings, list) and findings:
        print("Key findings")
        print("------------")
        for item in findings:
            print(f"- {item}")
        print()

    steps = summary.get("recommended_next_steps", [])
    if isinstance(steps, list) and steps:
        print("Recommended next steps")
        print("----------------------")
        for item in steps:
            print(f"- {item}")
        print()

    commands = summary.get("safe_commands", [])
    if isinstance(commands, list) and commands:
        print("Safe commands")
        print("-------------")
        for item in commands:
            print(f"  {item}")
        print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal doctor-summary",
        description="Run mqlaunch doctor --json and summarize the result.",
    )
    parser.add_argument("--repo", help="Configured repo name. Defaults to config default_repo.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    parser.add_argument("--no-ai", action="store_true", help="Skip Ollama and use deterministic fallback.")
    parser.add_argument("--sample", action="store_true", help="Use embedded sample doctor JSON for smoke tests.")

    args = parser.parse_args(argv)

    if args.sample:
        repo_name = args.repo or "sample"
        repo_path = Path.cwd()
        command = "sample doctor json"
        data = SAMPLE_DOCTOR_JSON
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data, _raw, command = run_doctor(repo_path)

    fallback = deterministic_summary(data)
    ai_summary = None if args.no_ai else call_ollama_summary(data, repo_name, command)
    summary = ai_summary or fallback
    used_ai = ai_summary is not None

    if args.json:
        print(json.dumps(
            {"repo": repo_name, "command": command, "used_ai": used_ai, "summary": summary},
            indent=2, ensure_ascii=False,
        ))
        return 0

    render(summary, repo_name, repo_path, command, used_ai)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
