#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: model-test"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/model_test.py"

echo "[2/4] sample output works"
"$ROOT/bin/mq-hal" model-test --sample >/dev/null

echo "[3/4] sample --json produces valid JSON"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "model-test", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("profile", "model", "ok", "latency_ms", "response"):
    assert key in d, f"missing key: {key}"
assert d["ok"] is True, d
print("  sample JSON shape: OK")
EOF

echo "[4/4] unknown profile fails clearly"
if "$ROOT/bin/mq-hal" model-test --profile missing-profile >/tmp/mq-hal-model-test-bad.out 2>&1; then
  echo "ERROR: unknown profile unexpectedly succeeded" >&2
  exit 1
fi
grep -q "unknown model profile" /tmp/mq-hal-model-test-bad.out
echo "  unknown profile rejected: OK"

echo "OK: model-test smoke test passed"
