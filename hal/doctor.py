#!/usr/bin/env python3
"""Doctor compatibility entrypoint for the mq-hal operator layer."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    script = BASE_DIR / "scripts" / "doctor_summary.py"
    return subprocess.call([sys.executable, str(script), *argv])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
