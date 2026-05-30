#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: models"

echo "[1/6] syntax check"
python3 -m py_compile "$ROOT/scripts/model_profiles.py"
python3 -m py_compile "$ROOT/scripts/models_list.py"

echo "[2/6] models output works"
"$ROOT/bin/mq-hal" models >/dev/null

echo "[3/6] models --json produces valid JSON with expected shape"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "models", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert "profiles" in d, "missing key: profiles"
assert "default" in d, "missing key: default"
for name in ("router", "planner", "critic", "code"):
    assert name in d["profiles"], f"missing profile: {name}"
    p = d["profiles"][name]
    assert "model" in p, f"profile {name} missing model"
    assert "reasoning_effort" in p, f"profile {name} missing reasoning_effort"
print(f"  {len(d['profiles'])} profiles, required keys OK: OK")
EOF

echo "[4/6] config/models.json is valid JSON"
python3 -c "import json; json.load(open('$ROOT/config/models.json'))"
echo "  config/models.json valid: OK"

echo "[5/6] router accepts model profile flag"
intent="$("$ROOT/bin/mq-hal" --model router --no-ai --raw-intent "visa git status i mq-hal")"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['intent']=='git_status'" <<< "$intent"
echo "  router --model profile: OK"

echo "[6/6] unknown model profile fails clearly"
if "$ROOT/bin/mq-hal" --model missing-profile --no-ai --raw-intent "visa git status i mq-hal" >/tmp/mq-hal-bad-model.out 2>&1; then
  echo "ERROR: unknown model profile unexpectedly succeeded" >&2
  exit 1
fi
grep -q "unknown model profile" /tmp/mq-hal-bad-model.out
echo "  unknown profile rejected: OK"

echo "OK: models smoke test passed"
