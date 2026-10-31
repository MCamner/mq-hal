#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from repo_status import resolve_repo

SAMPLE_INSPECT = {"core_files": [], "score": 0}
SAMPLE_DOCTOR = {"status": "ok", "checks": []}


def repo_signal_json(subcommand: str, repo_path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["repo-signal", subcommand, "--json", str(repo_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip() or f"repo-signal {subcommand} failed (exit {result.returncode})"}
        return json.loads(result.stdout)
    except Exception as exc:
        return {"error": str(exc)}


def build_repo_status_json(repo_name: str, repo_path: Path) -> dict[str, Any]:
    return {
        "repo": repo_name,
        "path": str(repo_path),
        "inspect": repo_signal_json("inspect", repo_path),
        "doctor": repo_signal_json("doctor", repo_path),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal repo-status-json")
    parser.add_argument("--repo")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    if args.sample:
        repo_name = args.repo or "macos-scripts"
        data: dict[str, Any] = {
            "repo": repo_name,
            "path": f"~/{repo_name}",
            "inspect": SAMPLE_INSPECT,
            "doctor": SAMPLE_DOCTOR,
        }
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        data = build_repo_status_json(repo_name, repo_path)

    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
