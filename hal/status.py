#!/usr/bin/env python3
"""Status command for the mq-hal operator layer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hal import stack
else:
    from . import stack


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal status",
        description="Show MQ stack status from mq-agent cockpit JSON.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    if args.sample:
        data = stack.SAMPLE_COCKPIT
        if args.json:
            stack.print_json(data)
        else:
            stack.render(data)
        return 0

    result = stack.read_cockpit()
    if not result.ok or result.data is None:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "warn",
                        "source": "mq-agent stack cockpit --json",
                        "error": result.error,
                        "returncode": result.returncode,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print("MQ Stack")
            print()
            print("mq-agent cockpit  WARN")
            print()
            print("Overall:")
            print("unknown")
            print()
            print(result.error)
        return 1

    if args.json:
        stack.print_json(result.data)
    else:
        stack.render(result.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
