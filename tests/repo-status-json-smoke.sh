#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: repo-status-json"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/repo_status_json.py"

echo "[2/4] --sample prints pure JSON with expected keys"
json_out="$("$ROOT/bin/mq-hal" repo-status-json --sample)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert 'repo' in d and 'path' in d and 'inspect' in d and 'doctor' in d" <<< "$json_out"

echo "[3/4] --repo is accepted (mq-mcp hal_repo_report passes it)"
json_out="$("$ROOT/bin/mq-hal" repo-status-json --sample --repo mq-mcp)"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['repo'] == 'mq-mcp', d['repo']" <<< "$json_out"

echo "[4/4] unknown repo fails with exit 2 instead of falling back"
set +e
"$ROOT/bin/mq-hal" repo-status-json --repo no-such-repo >/dev/null 2>&1
code=$?
set -e
if [[ "$code" -ne 2 ]]; then
  echo "expected exit 2 for unknown repo, got $code" >&2
  exit 1
fi

echo "OK: repo-status-json smoke test passed"
