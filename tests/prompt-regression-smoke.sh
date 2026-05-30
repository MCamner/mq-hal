#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: prompt regression"

python3 - <<EOF
import json
import subprocess

cases = [
    ("visa git status i mq-hal", "git_status", "mq-hal"),
    ("visa senaste commits i mq-hal", "git_log", "mq-hal"),
    ("hitta OLLAMA_MODEL i mq-hal", "grep_repo", "mq-hal"),
    ("kör tester i mq-hal", "run_test", "mq-hal"),
    ("repo-status-json i mq-hal", "repo_status_json", "mq-hal"),
]

for prompt, intent, repo in cases:
    r = subprocess.run(
        ["$ROOT/bin/mq-hal", "--no-ai", "--raw-intent", prompt],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (prompt, r.returncode, r.stderr)
    data = json.loads(r.stdout)
    assert data["intent"] == intent, (prompt, data)
    assert data["repo"] == repo, (prompt, data)

print(f"  {len(cases)} deterministic prompt routes: OK")
EOF

echo "OK: prompt regression smoke test passed"
