#!/usr/bin/env python3
"""mq-hal update helper."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, check=False)
    except OSError as exc:
        return 1, str(exc)
    output = (result.stdout or "") + (result.stderr or "")
    return int(result.returncode), output.strip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal update")
    parser.add_argument("--confirm", action="store_true", help="Run git pull in this repo")
    parser.add_argument("--json", dest="json_out", action="store_true")
    args = parser.parse_args(argv)

    commands = [["git", "pull", "--ff-only"]]
    data: dict[str, Any] = {
        "root": str(BASE_DIR),
        "confirmed": args.confirm,
        "commands": [" ".join(cmd) for cmd in commands],
        "status": "dry-run",
        "output": "",
    }

    if args.confirm:
        code, output = run(commands[0])
        data["status"] = "ok" if code == 0 else "fail"
        data["output"] = output
    else:
        data["output"] = "Run mq-hal update --confirm to execute."

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("HAL Update")
        print("==========")
        print()
        print(f"Root: {data['root']}")
        print(f"Status: {data['status']}")
        print()
        print("Commands")
        print("--------")
        for command in data["commands"]:
            print(f"- {command}")
        print()
        print(data["output"])

    return 0 if data["status"] in {"dry-run", "ok"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
