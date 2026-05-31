#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

CONFIG_PATH="$STATE_DIR/repos.json"
export MQ_HAL_STATE_DIR="$STATE_DIR"
export MQ_HAL_CONFIG_PATH="$CONFIG_PATH"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

printf '{"default_repo":"mq-hal","repos":{"mq-hal":"%s"}}\n' "$ROOT" >"$CONFIG_PATH"

echo "SMOKE: repo-memory"

echo "[1/6] syntax check"
python3 -m py_compile "$ROOT/scripts/repo_memory.py"

echo "[2/6] index builds local repo memory"
"$ROOT/bin/mq-hal" index mq-hal >/tmp/mq-hal-index.out
grep -q "^HAL Repo Memory Index" /tmp/mq-hal-index.out
test -f "$STATE_DIR/repo_memory/mq-hal.json"
echo "  index written: OK"

echo "[3/6] search finds roadmap content"
"$ROOT/bin/mq-hal" search roadmap --repo mq-hal >/tmp/mq-hal-search.out
grep -q "^HAL Repo Memory Search" /tmp/mq-hal-search.out
grep -q "ROADMAP.md" /tmp/mq-hal-search.out
echo "  search result: OK"

echo "[4/6] ask-repo returns grounded context"
"$ROOT/bin/mq-hal" ask-repo "what is the roadmap" --repo mq-hal >/tmp/mq-hal-ask.out
grep -q "^HAL Repo Answer" /tmp/mq-hal-ask.out
grep -q "Most relevant context" /tmp/mq-hal-ask.out
echo "  ask-repo output: OK"

echo "[5/6] repo-map summarizes indexed structure"
"$ROOT/bin/mq-hal" repo-map --repo mq-hal >/tmp/mq-hal-map.out
grep -q "^HAL Repo Map" /tmp/mq-hal-map.out
grep -q "Directories" /tmp/mq-hal-map.out
echo "  repo-map output: OK"

echo "[6/6] JSON modes have expected shape"
python3 - <<EOF
import json, os, subprocess
env = os.environ.copy()
env["MQ_HAL_STATE_DIR"] = "$STATE_DIR"
env["MQ_HAL_CONFIG_PATH"] = "$CONFIG_PATH"
env["PYTHONPYCACHEPREFIX"] = "$STATE_DIR/pycache"
cmds = [
    ["$ROOT/bin/mq-hal", "search", "roadmap", "--repo", "mq-hal", "--json"],
    ["$ROOT/bin/mq-hal", "ask-repo", "roadmap", "--repo", "mq-hal", "--json"],
    ["$ROOT/bin/mq-hal", "repo-map", "--repo", "mq-hal", "--json"],
]
for cmd in cmds:
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, (cmd, r.returncode, r.stderr)
    data = json.loads(r.stdout)
    assert isinstance(data, dict), data
print("  JSON modes: OK")
EOF

echo "OK: repo-memory smoke test passed"
