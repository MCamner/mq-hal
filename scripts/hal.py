#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from model_profiles import model_for_profile

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system.txt"
STATE_DIR = Path(os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))).expanduser()
STATE_PATH = STATE_DIR / "state.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "qwen3:4b-instruct"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
INTENT_SCHEMA_VERSION = "mq-hal.intent.v1"

ALLOWED_INTENTS = {
    "help",
    "list_repos",
    "switch_repo",
    "print_cd",
    "pwd",
    "repo_tree",
    "git_status",
    "git_log",
    "grep_repo",
    "run_test",
    "open_editor",
    "create_branch",
    "run_mqlaunch",
    "repo_status_json",
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
        "schema": {
            "type": "string",
            "enum": [INTENT_SCHEMA_VERSION],
        },
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
        "risk_level": {
            "type": ["string", "null"],
            "enum": ["low", "medium", "high", "unknown", None],
        },
        "rollback_plan": {
            "type": ["string", "null"],
        },
        "requires_confirmation": {
            "type": ["boolean", "null"],
        },
    },
    "required": ["schema", "intent", "repo", "command", "args", "message"],
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


def model_prompt(user_prompt: str) -> str:
    config = load_config()
    state = load_state(config)
    active_repo = state.get("active_repo", config.get("default_repo", ""))
    last_prompt = state.get("last_prompt")
    last_intent = state.get("last_intent")

    context = {
        "active_repo": active_repo,
        "configured_repos": sorted(config.get("repos", {}).keys()),
        "last_prompt": last_prompt if isinstance(last_prompt, str) else None,
        "last_intent": last_intent if isinstance(last_intent, dict) else None,
    }

    return (
        "Context JSON:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "User prompt:\n"
        f"{user_prompt}"
    )


def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str | None:
    payload = {
        "model": model,
        "system": system_prompt(),
        "prompt": model_prompt(prompt),
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
        print(
            "WARN: could not reach Ollama; trying deterministic fallback. "
            f"Start Ollama with: ollama pull {model}. Details: {exc}",
            file=sys.stderr,
        )
        return None
    except json.JSONDecodeError as exc:
        die(f"Ollama returned invalid JSON envelope: {exc}")

    text = body.get("response", "")
    if not isinstance(text, str) or not text.strip():
        die("Ollama returned an empty response")

    return text.strip()


def empty_intent(
    intent: str,
    message: str,
    repo: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
    risk_level: str | None = None,
    rollback_plan: str | None = None,
    requires_confirmation: bool | None = None,
) -> dict[str, Any]:
    return {
        "schema": INTENT_SCHEMA_VERSION,
        "intent": intent,
        "repo": repo,
        "command": command,
        "args": args or [],
        "message": message,
        "risk_level": risk_level,
        "rollback_plan": rollback_plan,
        "requires_confirmation": requires_confirmation,
    }


def find_repo_in_prompt(prompt: str, repos: dict[str, Path]) -> str | None:
    lowered = prompt.lower()
    for repo in sorted(repos, key=len, reverse=True):
        if repo.lower() in lowered:
            return repo
    return None


def deterministic_intent(prompt: str) -> dict[str, Any] | None:
    config = load_config()
    repos = load_repos(config)
    state = load_state(config)
    active = state.get("active_repo")
    repo = find_repo_in_prompt(prompt, repos)
    lowered = " ".join(prompt.lower().split())

    if repo is None and isinstance(active, str) and active in repos:
        repo = active

    if lowered in {"help", "hjälp", "--help"} or "hjälp" in lowered:
        return empty_intent("help", "Visar hjälp.")
    if "lista repo" in lowered or "list repos" in lowered or "vilka repo" in lowered:
        return empty_intent("list_repos", "Listar konfigurerade repos.")
    if lowered.startswith(("hitta ", "sök ", "search ", "grep ")):
        query = re.sub(r"^(hitta|sök|search|grep)\s+", "", prompt, flags=re.IGNORECASE).strip()
        if repo:
            query = re.sub(rf"\s+(i|in)\s+{re.escape(repo)}\s*$", "", query, flags=re.IGNORECASE).strip()
        return empty_intent("grep_repo", f"Söker efter: {query}", repo=repo, args=[query] if query else [])
    if lowered.startswith(("öppna ", "open ")):
        target = re.sub(r"^(öppna|open)\s+", "", prompt, flags=re.IGNORECASE).strip()
        if repo:
            target = re.sub(rf"\s+(i|in)\s+{re.escape(repo)}\s*$", "", target, flags=re.IGNORECASE).strip()
        return empty_intent("open_editor", f"Öppnar: {target}", repo=repo, args=[target] if target else [])
    if "skapa branch" in lowered or "ny branch" in lowered or "create branch" in lowered:
        branch = re.sub(
            r".*(skapa branch|ny branch|create branch)\s+",
            "",
            prompt,
            flags=re.IGNORECASE,
        ).strip()
        if repo:
            branch = re.sub(rf"\s+(i|in)\s+{re.escape(repo)}\s*$", "", branch, flags=re.IGNORECASE).strip()
        return empty_intent("create_branch", f"Skapar git branch: {branch}", repo=repo, args=[branch] if branch else [])
    if "repo-status-json" in lowered or "repo status json" in lowered or "inspect json" in lowered:
        return empty_intent("repo_status_json", "Hämtar strukturerad repo-status (inspect.v1 + doctor.v1).", repo=repo)
    if "git status" in lowered or "status" in lowered:
        return empty_intent("git_status", "Visar git status.", repo=repo)
    if "git log" in lowered or "senaste commit" in lowered or "commits" in lowered:
        return empty_intent("git_log", "Visar senaste commits.", repo=repo)
    if "träd" in lowered or "tree" in lowered or "filer" in lowered:
        return empty_intent("repo_tree", "Visar repo-filer.", repo=repo)
    if "kör tester" in lowered or "run tests" in lowered or "testerna" in lowered:
        return empty_intent("run_test", "Kör säkra repo-tester.", repo=repo)
    for command in sorted(ALLOWED_MQLAUNCH, key=len, reverse=True):
        if command in lowered:
            return empty_intent("run_mqlaunch", f"Kör mqlaunch {command}.", repo=repo, command=command)

    return None


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

    risk_raw = parsed.get("risk_level")
    risk_level = (
        str(risk_raw) if isinstance(risk_raw, str)
        and risk_raw in ("low", "medium", "high", "unknown")
        else None
    )
    rollback_raw = parsed.get("rollback_plan")
    rollback_plan = str(rollback_raw) if isinstance(rollback_raw, str) else None
    req_conf_raw = parsed.get("requires_confirmation")
    requires_confirmation = (
        bool(req_conf_raw) if isinstance(req_conf_raw, bool) else None
    )

    normalized = {
        "schema": str(parsed.get("schema", INTENT_SCHEMA_VERSION)),
        "intent": intent,
        "repo": parsed.get("repo"),
        "command": parsed.get("command"),
        "args": [str(item) for item in args],
        "message": str(parsed.get("message", "")),
        "risk_level": risk_level,
        "rollback_plan": rollback_plan,
        "requires_confirmation": requires_confirmation,
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


def command_text(command: list[str]) -> str:
    return " ".join(command)


def confirm_command(command: list[str], cwd: Path | None) -> bool:
    location = str(cwd) if cwd else str(Path.cwd())
    print("HAL preview")
    print("===========")
    print(f"cwd:     {location}")
    print(f"command: {command_text(command)}")
    print()
    answer = input("Run this command? [y/N] ").strip().lower()
    return answer in {"y", "yes", "j", "ja"}


def run_planned_command(command: list[str], cwd: Path | None = None, confirm: bool = False) -> int:
    if confirm and not confirm_command(command, cwd):
        print("Cancelled.")
        return 130
    return run_command(command, cwd=cwd)


def is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


def intent_text_arg(intent: dict[str, Any]) -> str:
    args = intent.get("args", [])
    if isinstance(args, list) and args:
        return " ".join(str(item) for item in args).strip()
    command = intent.get("command")
    return command.strip() if isinstance(command, str) else ""


def resolve_repo_path_arg(repo_path: Path, text: str) -> Path | None:
    target = text.strip() or "."
    candidate = (repo_path / target).expanduser().resolve()
    if not is_within(repo_path.resolve(), candidate):
        return None
    return candidate


def test_command_for_repo(repo_path: Path) -> list[str] | None:
    if (repo_path / "tests" / "smoke.sh").exists():
        return ["bash", "tests/smoke.sh"]
    if (repo_path / "scripts" / "validate.sh").exists():
        return ["bash", "scripts/validate.sh"]
    if (repo_path / "pyproject.toml").exists() and (repo_path / "tests").exists():
        return ["python3", "-m", "pytest"]
    if (repo_path / "package.json").exists():
        return ["npm", "test"]
    return None


def editor_command_for_path(path: Path) -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return [editor, str(path)]
    if shutil.which("code"):
        return ["code", str(path)]
    if shutil.which("open"):
        return ["open", str(path)]
    return ["nano", str(path)]


def valid_branch_name(name: str) -> bool:
    if not name or len(name) > 120:
        return False
    if name.startswith(("-", "/", ".")) or name.endswith(("/", ".", ".lock")):
        return False
    if any(part in name for part in ("..", "//", "@{", "\\")):
        return False
    return re.fullmatch(r"[A-Za-z0-9._/-]+", name) is not None


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


def explain_intent(intent: dict[str, Any]) -> None:
    config = load_config()
    repos = load_repos(config)
    state = load_state(config)
    repo_name, repo_path = resolve_repo(intent, repos, state)
    print(json.dumps(intent, indent=2, ensure_ascii=False))
    print()
    print("Resolved")
    print("--------")
    print(f"repo: {repo_name}")
    print(f"path: {repo_path}")
    print(f"intent: {intent.get('intent')}")


def remember_prompt(prompt: str, intent: dict[str, Any]) -> None:
    config = load_config()
    state = load_state(config)
    state["last_prompt"] = prompt
    state["last_intent"] = intent
    save_state(state)


def handle_intent(intent: dict[str, Any], confirm: bool = False) -> int:
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

    # refuse and mqlaunch rejection do not require a real repo path
    if action == "refuse":
        if not message:
            print("HAL: Jag kan inte göra det där säkert.")
        return 2

    if action == "run_mqlaunch":
        command = intent.get("command")
        if not isinstance(command, str):
            print("ERROR: missing mqlaunch command", file=sys.stderr)
            return 2
        normalized = command.strip().lower().replace("_", "-")
        if normalized not in ALLOWED_MQLAUNCH:
            print(
                f"ERROR: mqlaunch command not allowed: {command}",
                file=sys.stderr,
            )
            print("Allowed:")
            for item in sorted(ALLOWED_MQLAUNCH):
                print(f"- {item}")
            return 2

    repo_name, repo_path = resolve_repo(intent, repos, state)
    ensure_repo_exists(repo_name, repo_path)

    if action == "pwd":
        print(repo_path)
        return 0

    if action == "repo_tree":
        print_repo_tree(repo_path)
        return 0

    if action == "git_status":
        return run_planned_command(["git", "status", "--short"], cwd=repo_path, confirm=confirm)

    if action == "git_log":
        return run_planned_command(["git", "log", "--oneline", "-n", "8"], cwd=repo_path, confirm=confirm)

    if action == "grep_repo":
        query = intent_text_arg(intent)
        if not query:
            print("ERROR: missing search query", file=sys.stderr)
            return 2
        return run_planned_command(["rg", "-n", "--", query], cwd=repo_path, confirm=confirm)

    if action == "run_test":
        command = test_command_for_repo(repo_path)
        if command is None:
            print(f"ERROR: no safe test command detected for repo: {repo_name}", file=sys.stderr)
            return 2
        return run_planned_command(command, cwd=repo_path, confirm=confirm)

    if action == "open_editor":
        target = resolve_repo_path_arg(repo_path, intent_text_arg(intent))
        if target is None:
            print("ERROR: refusing to open a path outside the repo", file=sys.stderr)
            return 2
        return run_planned_command(editor_command_for_path(target), cwd=repo_path, confirm=confirm)

    if action == "create_branch":
        branch = intent_text_arg(intent)
        if not valid_branch_name(branch):
            print(f"ERROR: invalid branch name: {branch}", file=sys.stderr)
            return 2
        return run_planned_command(["git", "checkout", "-b", branch], cwd=repo_path, confirm=True if not confirm else confirm)

    if action == "repo_status_json":
        import json as _json
        output: dict = {"repo": repo_name, "path": str(repo_path)}
        try:
            inspect_result = subprocess.run(
                ["repo-signal", "inspect", "--json", str(repo_path)],
                capture_output=True, text=True, timeout=30,
            )
            output["inspect"] = _json.loads(inspect_result.stdout) if inspect_result.returncode == 0 else {"error": inspect_result.stderr.strip()}
        except Exception as exc:
            output["inspect"] = {"error": str(exc)}
        try:
            doctor_result = subprocess.run(
                ["repo-signal", "doctor", "--json", str(repo_path)],
                capture_output=True, text=True, timeout=30,
            )
            output["doctor"] = _json.loads(doctor_result.stdout) if doctor_result.returncode == 0 else {"error": doctor_result.stderr.strip()}
        except Exception as exc:
            output["doctor"] = {"error": str(exc)}
        print(_json.dumps(output, indent=2, ensure_ascii=False))
        return 0

    if action == "run_mqlaunch":
        command = str(intent.get("command", ""))
        normalized = command.strip().lower().replace("_", "-")
        return run_planned_command(
            ALLOWED_MQLAUNCH[normalized], cwd=repo_path, confirm=confirm
        )

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
    parser.add_argument("--explain-intent", "--why", action="store_true", help="Print parsed intent and resolved repo")
    parser.add_argument("--confirm", action="store_true", help="Preview routed commands and ask before running")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic fallback routing without Ollama")
    parser.add_argument("--model", help="Model profile from config/models.json")

    args = parser.parse_args(argv)

    if args.cd_repo:
        return direct_cd(args.cd_repo)

    if args.list_repos:
        return list_repos()

    prompt = " ".join(args.prompt).strip()

    if not prompt:
        parser.print_help()
        return 0

    try:
        model, _profile = model_for_profile(
            args.model,
            default_profile="router",
            env_default=DEFAULT_OLLAMA_MODEL,
        )
    except ValueError as exc:
        die(str(exc))

    raw = None if args.no_ai else call_ollama(prompt, model=model)
    if raw is None:
        intent = deterministic_intent(prompt)
        if intent is None:
            die(
                "could not route prompt without Ollama. Start Ollama first, "
                f"then run: ollama pull {model}"
            )
    else:
        intent = parse_intent(raw)

    if args.raw_intent:
        print(json.dumps(intent, indent=2, ensure_ascii=False))
        return 0

    if args.explain_intent:
        explain_intent(intent)
        return 0

    remember_prompt(prompt, intent)
    return handle_intent(intent, confirm=args.confirm)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
