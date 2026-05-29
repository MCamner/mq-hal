#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: agent-brief"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/agent_brief.py"

echo "[2/4] sample text output works"
"$ROOT/bin/mq-hal" agent-brief --sample >/dev/null

echo "[3/4] sample --json produces valid JSON with expected keys"
python3 - <<EOF
import json, subprocess, sys
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "agent-brief", "--sample", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
assert "available" in d, "missing key: available"
assert "memory" in d, "missing key: memory"
mem = d["memory"]
for key in ("available", "status", "enabled", "repo_signal_available"):
    assert key in mem, f"missing memory key: {key}"
print("  keys OK:", list(d.keys()))
EOF

echo "[4/4] fallback when mq-agent absent"
python3 - "$ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import agent_brief as ab
original = ab.find_mq_agent
ab.find_mq_agent = lambda: None
data = ab.collect()
ab.find_mq_agent = original
assert not data["available"]
assert data["memory"]["status"] == "mq-agent-unavailable"
print("  fallback when missing: OK")
PYEOF

echo "OK: agent-brief smoke test passed"
