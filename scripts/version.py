#!/usr/bin/env python3
"""mq-hal version command."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def read_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal version")
    parser.add_argument("--json", dest="json_out", action="store_true")
    args = parser.parse_args(argv)

    data = {
        "version": read_text(BASE_DIR / "VERSION", "unknown"),
        "root": str(BASE_DIR),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }

    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"mq-hal {data['version']}")
        print(f"root: {data['root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
