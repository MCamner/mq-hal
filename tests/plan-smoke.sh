#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: plan"

echo "[1/9] syntax check"
python3 -m py_compile "$ROOT/scripts/planner.py"

echo "[2/9] sample output works"
"$ROOT/bin/mq-hal" plan --sample >/dev/null

echo "[3/9] sample output contains expected sections"
out="$("$ROOT/bin/mq-hal" plan --sample)"
echo "$out" | grep -q "^HAL Plan"
echo "$out" | grep -q "Goal:"
echo "$out" | grep -q "Risk:"
echo "$out" | grep -q "Steps"
echo "  sections found: OK"

echo "[4/9] sample --json produces valid JSON with required keys"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "plan", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("goal", "affected_repos", "affected_files",
            "risk", "steps", "validation", "rollback_plan"):
    assert key in d, f"missing key: {key}"
assert d["risk"] in ("low", "medium", "high", "unknown"), \
    f"invalid risk: {d['risk']}"
assert isinstance(d["steps"], list), "steps must be a list"
print(f"  keys OK, risk={d['risk']}, {len(d['steps'])} steps: OK")
EOF

echo "[5/9] --out saves plan to file"
PLAN_FILE="$STATE_DIR/plan.json"
"$ROOT/bin/mq-hal" plan --sample --out "$PLAN_FILE" >/dev/null
python3 -c "
import json
d = json.load(open('$PLAN_FILE'))
assert 'goal' in d, 'missing goal in saved plan'
print('  plan saved and valid: OK')
"

echo "[6/9] --no-ai returns stub plan with goal"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "plan", "--no-ai", "--json",
     "test goal for smoke"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert "test goal for smoke" in d["goal"], \
    f"goal not in stub plan: {d['goal']}"
assert d["risk"] == "unknown", f"stub plan risk should be unknown: {d['risk']}"
print("  --no-ai stub plan: OK")
EOF

echo "[7/9] --model profile parses with no-ai"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "plan", "--model", "planner", "--no-ai", "--json",
     "model profile smoke"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert "model profile smoke" in d["goal"], d["goal"]
print("  plan --model profile: OK")
EOF

echo "[8/9] parse_plan recovers JSON embedded in prose"
python3 - <<EOF
import sys
sys.path.insert(0, "$ROOT/scripts")
import planner
wrapped = '''
Here is the plan:
{
  "goal": "embedded json",
  "affected_repos": ["mq-hal"],
  "affected_files": ["README.md"],
  "risk": "low",
  "steps": [
    {
      "id": 1,
      "description": "inspect README",
      "safe_command": "cat README.md",
      "requires_confirm": false
    }
  ],
  "validation": ["cat README.md exits 0"],
  "rollback_plan": "No changes"
}
'''
plan = planner.parse_plan(wrapped)
assert plan is not None, "expected embedded JSON to parse"
assert plan["goal"] == "embedded json", plan
print("  embedded JSON recovery: OK")
EOF

echo "[9/9] parse_plan rejects malformed model response"
python3 - <<EOF
import sys
sys.path.insert(0, "$ROOT/scripts")
import planner
bad = {
    "goal": "bad",
    "affected_repos": ["mq-hal"],
    "affected_files": [],
    "risk": "low",
    "steps": [{"id": "one", "description": "", "requires_confirm": "no"}],
    "validation": [],
    "rollback_plan": None,
}
assert planner.parse_plan("not json at all") is None
assert planner.parse_plan(__import__("json").dumps(bad)) is None
print("  malformed response rejected: OK")
EOF

echo "OK: plan smoke test passed"
