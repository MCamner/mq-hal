#!/usr/bin/env python3
"""Validate mq-hal local configuration files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing file: {path.relative_to(BASE_DIR)}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.relative_to(BASE_DIR)}: {exc}"
    except OSError as exc:
        return None, f"could not read {path.relative_to(BASE_DIR)}: {exc}"


def check_repos(strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    data, error = load_json(BASE_DIR / "config" / "repos.json")
    if error:
        return [error], warnings
    if not isinstance(data, dict):
        return ["config/repos.json must contain an object"], warnings
    repos = data.get("repos")
    if not isinstance(repos, dict) or not repos:
        errors.append("config/repos.json must contain a non-empty repos object")
        return errors, warnings
    default_repo = data.get("default_repo")
    if default_repo and default_repo not in repos:
        errors.append("config/repos.json default_repo must exist in repos")
    for name, raw_path in sorted(repos.items()):
        if not isinstance(name, str) or not name:
            errors.append("config/repos.json repo names must be non-empty strings")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"repo {name!r} path must be a non-empty string")
            continue
        path = Path(raw_path).expanduser()
        if not path.exists():
            message = f"repo {name!r} path does not exist: {path}"
            if strict:
                errors.append(message)
            else:
                warnings.append(message)
    return errors, warnings


def check_models() -> list[str]:
    errors: list[str] = []
    data, error = load_json(BASE_DIR / "config" / "models.json")
    if error:
        return [error]
    if not isinstance(data, dict):
        return ["config/models.json must contain an object"]
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("config/models.json must contain a non-empty profiles object")
    return errors


def check_tools() -> list[str]:
    sys.path.insert(0, str(BASE_DIR))
    from mq_hal.tools.registry import load_registry, validate_registry

    try:
        tools = load_registry(BASE_DIR / "config" / "tools.json")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"config/tools.json invalid: {exc}"]
    return validate_registry(tools)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal config-check")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail when configured repo paths are missing")
    args = parser.parse_args(argv)

    repo_errors, repo_warnings = check_repos(args.strict)
    errors = repo_errors + check_models() + check_tools()
    warnings = repo_warnings
    status = "ok" if not errors else "fail"
    data = {"status": status, "errors": errors, "warnings": warnings}

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("HAL Config Check")
        print("================")
        print()
        if errors:
            print("Errors")
            print("------")
            for item in errors:
                print(f"- {item}")
            print()
        if warnings:
            print("Warnings")
            print("--------")
            for item in warnings:
                print(f"- {item}")
            print()
        if not errors and not warnings:
            print("OK: config files look valid")
        elif not errors:
            print("OK: config files are valid with warnings")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
