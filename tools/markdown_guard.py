#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("README.md")
text = path.read_text(encoding="utf-8")
lines = text.splitlines()

errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

fence = chr(96) * 3
fence_lines = [i for i, line in enumerate(lines, start=1) if line.startswith(fence)]

require(len(lines) >= 180, f"README too short: {len(lines)} lines")
require(len(fence_lines) >= 30, f"Too few fenced blocks: {len(fence_lines)} fence lines")
require(len(fence_lines) % 2 == 0, f"Unbalanced markdown fences: {len(fence_lines)}")

bad_fences = [
    (i, line)
    for i, line in enumerate(lines, start=1)
    if line.startswith(fence) and " id=" in line
]
require(not bad_fences, f"Bad fence info strings: {bad_fences[:5]}")

required_strings = [
    "version-0.14.1",
    "## Proof",
    "## HAL Brief",
    "## HAL Release Brief",
    "## HAL Audit",
    "## HAL Stack Status",
    "## HAL Repo Ops",
    "## HAL Doctor Summary",
    "## HAL Fix Planner",
    "## HAL Session Memory",
    "## HAL Timeline UI",
    "docs/INTEGRATION.md",
    "docs/hal-command-surface.md",
    "mq-hal release-brief",
    "mq-hal audit",
    "mq-hal stack-status",
    "mq-hal repo-status",
    "mq-hal ci",
    "mqlaunch hal audit",
]

for item in required_strings:
    require(item in text, f"Missing required text: {item}")

bad_flattened_patterns = [
    "# 1. Install Ollama brew install",
    'mqhcd() { if [ $# -ne 1 ]; then',
    'return 2 fi local path',
    'return $? cd "$path"',
    'mq-hal remember "release looked good" mq-hal memory-path',
]

for pattern in bad_flattened_patterns:
    require(pattern not in text, f"Flattened markdown detected: {pattern}")

try:
    start = lines.index("mqhcd() {")
    end = lines.index("}", start)
    helper = lines[start:end + 1]
    require(len(helper) >= 8, "mqhcd helper is not multiline enough")
except ValueError:
    errors.append("mqhcd helper block not found as multiline fenced content")

if errors:
    print("README markdown guard failed:", file=sys.stderr)
    for err in errors:
        print(f"- {err}", file=sys.stderr)
    raise SystemExit(1)

print(f"OK: markdown guard passed for {path}")
