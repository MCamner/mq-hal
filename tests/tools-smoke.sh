#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: tools"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/tools_list.py"

echo "[2/4] tools output works"
"$ROOT/bin/mq-hal" tools >/dev/null

echo "[3/4] tools --json produces valid JSON with expected shape"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "tools", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert "tools" in d, "missing key: tools"
assert len(d["tools"]) > 0, "tools list is empty"
names = {t["name"] for t in d["tools"]}
for expected in ("brief", "audit", "doctor-summary", "hello"):
    assert expected in names, f"missing tool: {expected}"
print(f"  {len(d['tools'])} tools, required names present: OK")
EOF

echo "[4/4] config/tools.json is valid JSON"
python3 -c "import json; json.load(open('$ROOT/config/tools.json'))"
echo "  config/tools.json valid: OK"

echo "OK: tools smoke test passed"
