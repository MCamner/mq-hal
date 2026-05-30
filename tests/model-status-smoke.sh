#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: model-status"

echo "[1/5] syntax check"
python3 -m py_compile "$ROOT/scripts/model_status.py"

echo "[2/5] sample output works"
"$ROOT/bin/mq-hal" model-status --sample >/dev/null

echo "[3/5] sample output contains expected sections"
out="$("$ROOT/bin/mq-hal" model-status --sample)"
echo "$out" | grep -q "^HAL Model Status"
echo "$out" | grep -q "Reachable:"
echo "$out" | grep -q "PROFILE"
echo "  sections found: OK"

echo "[4/5] sample --json produces valid JSON with expected keys"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "model-status", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("ollama_url", "reachable", "latency_ms", "profiles"):
    assert key in d, f"missing key: {key}"
assert "router" in d["profiles"], "missing router profile"
print("  sample JSON shape: OK")
EOF

echo "[5/5] profile filter works"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "model-status", "--sample", "--json", "--profile", "planner"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert list(d["profiles"]) == ["planner"], d["profiles"]
print("  profile filter: OK")
EOF

echo "OK: model-status smoke test passed"
