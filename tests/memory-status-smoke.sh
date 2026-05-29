#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: memory-status"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/memory_status.py"

echo "[2/4] sample text output works"
"$ROOT/bin/mq-hal" memory-status --sample >/dev/null

echo "[3/4] sample --json produces valid JSON with expected keys"
python3 - <<EOF
import json, subprocess, sys
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "memory-status", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("available", "status", "enabled", "vector_store_id",
            "repo_signal_available", "repo_path"):
    assert key in d, f"missing key: {key}"
print("  keys OK:", list(d.keys()))
EOF

echo "[4/4] --brief --sample produces one-line output"
line="$("$ROOT/bin/mq-hal" memory-status --sample --brief)"
echo "$line" | grep -q "memory:" || {
  echo "ERROR: brief output missing 'memory:' prefix"
  exit 1
}
echo "  brief line: $line"

echo "OK: memory-status smoke test passed"
