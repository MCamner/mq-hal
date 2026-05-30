#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

PLAN_FILE="$STATE_DIR/plan.json"
BAD_PLAN_FILE="$STATE_DIR/bad-plan.json"

echo "SMOKE: execute"

echo "[1/5] syntax check"
python3 -m py_compile "$ROOT/scripts/executor.py"

echo "[2/5] dry-run preview works"
cat >"$PLAN_FILE" <<EOF
{
  "goal": "execute smoke plan",
  "affected_repos": ["mq-hal"],
  "affected_files": ["VERSION"],
  "risk": "low",
  "steps": [
    {
      "id": 1,
      "description": "Read version",
      "safe_command": "cat VERSION",
      "requires_confirm": false
    }
  ],
  "validation": ["cat VERSION exits 0"],
  "rollback_plan": "No files are changed."
}
EOF
out="$("$ROOT/bin/mq-hal" execute "$PLAN_FILE")"
echo "$out" | grep -q "^HAL Execute"
echo "$out" | grep -q "Steps (dry run"
echo "$out" | grep -q "mq-hal execute .* --confirm"
echo "  dry-run preview: OK"

echo "[3/5] --confirm runs safe non-interactive step"
"$ROOT/bin/mq-hal" execute "$PLAN_FILE" --confirm >/tmp/mq-hal-execute-smoke.out
grep -q "Done. 1 run, 0 skipped, 0 failed" /tmp/mq-hal-execute-smoke.out
echo "  confirmed execution: OK"

echo "[4/5] critic FAIL blocks dangerous plan"
cat >"$BAD_PLAN_FILE" <<EOF
{
  "goal": "bad execute smoke plan",
  "affected_repos": ["mq-hal"],
  "affected_files": [],
  "risk": "high",
  "steps": [
    {
      "id": 1,
      "description": "Dangerous delete",
      "safe_command": "rm -rf /tmp/mq-hal-danger",
      "requires_confirm": false
    }
  ],
  "validation": [],
  "rollback_plan": null
}
EOF
if "$ROOT/bin/mq-hal" execute "$BAD_PLAN_FILE" --confirm >/tmp/mq-hal-execute-bad.out 2>&1; then
  echo "ERROR: dangerous plan unexpectedly executed" >&2
  exit 1
fi
grep -q "critic returned FAIL" /tmp/mq-hal-execute-bad.out
echo "  critic fail blocks execution: OK"

echo "[5/5] shell operators are refused even if critic is skipped"
python3 - <<EOF
import json
from pathlib import Path
plan = json.loads(Path("$PLAN_FILE").read_text())
plan["steps"][0]["safe_command"] = "cat VERSION; echo unsafe"
Path("$BAD_PLAN_FILE").write_text(json.dumps(plan), encoding="utf-8")
EOF
if "$ROOT/bin/mq-hal" execute "$BAD_PLAN_FILE" --confirm --skip-critic >/tmp/mq-hal-execute-op.out 2>&1; then
  echo "ERROR: shell operator plan unexpectedly succeeded" >&2
  exit 1
fi
grep -q "shell operator detected" /tmp/mq-hal-execute-op.out
echo "  shell operator refused: OK"

echo "OK: execute smoke test passed"
