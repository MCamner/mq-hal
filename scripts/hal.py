#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system.txt"
STATE_DIR = Path.home() / ".mq-hal"
STATE_PATH = STATE_DIR / "state.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")

ALLOWED_INTENTS = {
    "help",
    "list_repos",
    "switch_repo",
    "print_cd",
    "pwd",
    "repo_tree",
    "git_status",
    "git_log",
    "run_mqlaunch",
    "refuse",
}

ALLOWED_MQLAUNCH = {
    "doctor": ["mqlaunch", "doctor"],
    "release-check": ["mqlaunch", "release-check"],
    "release_check": ["mqlaunch", "release-check"],
    "selftest": ["mqlaunch", "selftest"],
    "perf": ["mqlaunch", "perf"],
    "system-check": ["mqlaunch", "system", "check"],
    "system_check": ["mqlaunch", "system", "check"],
    "system check": ["mqlaunch", "system", "check"],
    "demo": ["mqlaunch", "demo"],
}

INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": sorted(ALLOWED_INTENTS),
        },
        "repo": {
            "type": ["string", "null"],
        },
        "command": {
            "type": ["string", "null"],
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
        },
        "message": {
            "type": "string",
        },
    },
    "required": ["intent", "repo", "command", "args", "message"],
    "additionalProperties": False,
}


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")


def load_config() -> dict[str, Any]:
    config = load_json(CONFIG_PATH)

    if "repos" not in config or not isinstance(config["repos"], dict):
        die("config/repos.json must contain a repos object")

    return config


def expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def load_repos(config: dict[str, Any]) -> dict[str, Path]:
    repos: dict[str, Path] = {}

    for name, raw_path in config["repos"].items():
        repos[name] = expand_path(str(raw_path))

    return repos


def load_state(config: dict[str, Any]) -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"active_repo": config.get("default_repo", "macos-scripts")}

    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"active_repo": config.get("default_repo", "macos-scripts")}

    if not isinstance(state, dict):
        return {"active_repo": config.get("default_repo", "macos-scripts")}

    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "system": system_prompt(),
        "prompt": prompt,
        "format": INTENT_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0
        },
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
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        die(
            "could not reach Ollama. Start Ollama first, then run: "
            f"ollama pull {OLLAMA_MODEL}. Details: {exc}"
        )
    except json.JSONDecodeError as exc:
        die(f"Ollama returned invalid JSON envelope: {exc}")

    text = body.get("response", "")
    if not isinstance(text, str) or not text.strip():
        die("Ollama returned an empty response")

    return text.strip()


def parse_intent(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {
                "intent": "refuse",
                "repo": None,
                "command": None,
                "args": [],
                "message": "Jag kunde inte tolka modellens svar som JSON.",
            }

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {
                "intent": "refuse",
                "repo": None,
                "command": None,
                "args": [],
                "message": "Jag kunde inte extrahera giltig JSON från modellens svar.",
            }

    if not isinstance(parsed, dict):
        return {
            "intent": "refuse",
            "repo": None,
            "command": None,
            "args": [],
            "message": "Modellen returnerade inte ett JSON-objekt.",
        }

    intent = str(parsed.get("intent", "refuse"))
    if intent not in ALLOWED_INTENTS:
        intent = "refuse"

    args = parsed.get("args", [])
    if not isinstance(args, list):
        args = []

    normalized = {
        "intent": intent,
        "repo": parsed.get("repo"),
        "command": parsed.get("command"),
        "args": [str(item) for item in args],
        "message": str(parsed.get("message", "")),
    }

    return normalized


def resolve_repo(
    intent: dict[str, Any],
    repos: dict[str, Path],
    state: dict[str, Any],
) -> tuple[str, Path]:
    requested = intent.get("repo")

    if isinstance(requested, str) and requested in repos:
        return requested, repos[requested]

    active = state.get("active_repo")
    if isinstance(active, str) and active in repos:
        return active, repos[active]

    first_name = next(iter(repos.keys()))
    return first_name, repos[first_name]


def ensure_repo_exists(repo_name: str, repo_path: Path) -> None:
    if not repo_path.exists():
        die(f"repo '{repo_name}' does not exist at {repo_path}")

    if not repo_path.is_dir():
        die(f"repo '{repo_name}' is not a directory: {repo_path}")


def run_command(command: list[str], cwd: Path | None = None) -> int:
    try:
        completed = subprocess.run(command, cwd=str(cwd) if cwd else None)
    except FileNotFoundError:
        print(f"ERROR: command not found: {command[0]}", file=sys.stderr)
        return 127

    return int(completed.returncode)


def print_repo_tree(repo_path: Path, max_items: int = 80) -> None:
    ignored = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }

    files: list[str] = []

    for path in repo_path.rglob("*"):
        rel = path.relative_to(repo_path)

        if any(part in ignored for part in rel.parts):
            continue

        if path.is_file():
            files.append(str(rel))

        if len(files) >= max_items:
            break

    for item in sorted(files):
        print(item)


def handle_intent(intent: dict[str, Any]) -> int:
    config = load_config()
    repos = load_repos(config)
    state = load_state(config)

    action = intent["intent"]
    message = intent.get("message", "")

    if message and action != "print_cd":
        print(f"HAL: {message}")

    if action == "help":
        print(
            """
mq-hal commands:
  fråga naturligt:
    mq-hal "visa git status i macos-scripts"
    mq-hal "kör doctor"
    mq-hal "byt till repo-signal"
    mq-hal "visa senaste commits"

  direkta helpers:
    mq-hal --list-repos
    mq-hal --cd repo-signal
""".strip()
        )
        return 0

    if action == "list_repos":
        for name, path in repos.items():
            marker = "*" if state.get("active_repo") == name else " "
            print(f"{marker} {name:16} {path}")
        return 0

    if action == "switch_repo":
        repo = intent.get("repo")

        if not isinstance(repo, str) or repo not in repos:
            print("Tillgängliga repos:")
            for name in repos:
                print(f"- {name}")
            return 2

        repo_path = repos[repo]
        ensure_repo_exists(repo, repo_path)

        state["active_repo"] = repo
        save_state(state)

        print(f"Active repo: {repo}")
        print(f"Path: {repo_path}")
        print()
        print(f"För att gå dit i shell:")
        print(f"cd {repo_path}")
        return 0

    if action == "print_cd":
        repo = intent.get("repo")

        if not isinstance(repo, str) or repo not in repos:
            return 2

        repo_path = repos[repo]
        ensure_repo_exists(repo, repo_path)
        print(repo_path)
        return 0

    repo_name, repo_path = resolve_repo(intent, repos, state)
    ensure_repo_exists(repo_name, repo_path)

    if action == "pwd":
        print(repo_path)
        return 0

    if action == "repo_tree":
        print_repo_tree(repo_path)
        return 0

    if action == "git_status":
        return run_command(["git", "status", "--short"], cwd=repo_path)

    if action == "git_log":
        return run_command(["git", "log", "--oneline", "-n", "8"], cwd=repo_path)

    if action == "run_mqlaunch":
        command = intent.get("command")

        if not isinstance(command, str):
            print("ERROR: missing mqlaunch command", file=sys.stderr)
            return 2

        normalized = command.strip().lower().replace("_", "-")

        if normalized not in ALLOWED_MQLAUNCH:
            print(f"ERROR: mqlaunch command not allowed: {command}", file=sys.stderr)
            print("Allowed:")
            for item in sorted(ALLOWED_MQLAUNCH):
                print(f"- {item}")
            return 2

        return run_command(ALLOWED_MQLAUNCH[normalized], cwd=repo_path)

    if action == "refuse":
        if not message:
            print("HAL: Jag kan inte göra det där säkert.")
        return 2

    print(f"ERROR: unhandled intent: {action}", file=sys.stderr)
    return 2


def direct_cd(repo_name: str) -> int:
    config = load_config()
    repos = load_repos(config)

    if repo_name not in repos:
        print(f"ERROR: unknown repo: {repo_name}", file=sys.stderr)
        print("Known repos:", ", ".join(sorted(repos)), file=sys.stderr)
        return 2

    repo_path = repos[repo_name]
    ensure_repo_exists(repo_name, repo_path)
    print(repo_path)
    return 0


def list_repos() -> int:
    config = load_config()
    repos = load_repos(config)
    state = load_state(config)

    for name, path in repos.items():
        marker = "*" if state.get("active_repo") == name else " "
        print(f"{marker} {name:16} {path}")

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal",
        description="Local HAL command router for Ollama + mqlaunch.",
    )

    parser.add_argument("prompt", nargs="*", help="Natural language prompt")
    parser.add_argument("--cd", dest="cd_repo", help="Print repo path")
    parser.add_argument("--list-repos", action="store_true", help="List known repos")
    parser.add_argument("--raw-intent", action="store_true", help="Print parsed intent only")

    args = parser.parse_args(argv)

    if args.cd_repo:
        return direct_cd(args.cd_repo)

    if args.list_repos:
        return list_repos()

    prompt = " ".join(args.prompt).strip()

    if not prompt:
        parser.print_help()
        return 0

    raw = call_ollama(prompt)
    intent = parse_intent(raw)

    if args.raw_intent:
        print(json.dumps(intent, indent=2, ensure_ascii=False))
        return 0

    return handle_intent(intent)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
