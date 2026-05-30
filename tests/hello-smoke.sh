#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: hello"

echo "[1/5] syntax check"
python3 -m py_compile "$ROOT/scripts/hello.py"

echo "[2/5] sample output works"
"$ROOT/bin/mq-hal" hello --sample >/dev/null

echo "[3/5] sample output contains expected sections"
out="$("$ROOT/bin/mq-hal" hello --sample)"
echo "$out" | grep -q "^HAL"
echo "$out" | grep -q "Active repo:"
echo "$out" | grep -q "Commands"
echo "  sections found: OK"

echo "[4/5] sample --json produces valid JSON with expected keys"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "hello", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("active_repo", "version", "memory_brief", "recent_events"):
    assert key in d, f"missing key: {key}"
print("  keys OK:", list(d.keys()))
EOF

echo "[5/5] status-screen alias works"
"$ROOT/bin/mq-hal" status-screen --sample >/dev/null
echo "  status-screen alias: OK"

echo "OK: hello smoke test passed"
