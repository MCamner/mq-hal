#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: hal router"

echo "[1/6] syntax check"
python3 -m py_compile "$ROOT/scripts/hal.py"

echo "[2/6] deterministic raw intent includes schema"
intent="$("$ROOT/bin/mq-hal" --no-ai --raw-intent "visa git status i mq-hal")"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['schema']=='mq-hal.intent.v1'; assert d['intent']=='git_status'; assert d['repo']=='mq-hal'" <<< "$intent"

echo "[3/6] grep intent routes safely"
grep_intent="$("$ROOT/bin/mq-hal" --no-ai --raw-intent "hitta OLLAMA_MODEL i mq-hal")"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['intent']=='grep_repo'; assert d['args']==['OLLAMA_MODEL']" <<< "$grep_intent"

echo "[4/6] test intent routes safely"
test_intent="$("$ROOT/bin/mq-hal" --no-ai --raw-intent "kör tester i mq-hal")"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['intent']=='run_test'; assert d['repo']=='mq-hal'" <<< "$test_intent"

echo "[5/6] branch intent routes safely"
branch_intent="$("$ROOT/bin/mq-hal" --no-ai --raw-intent "skapa branch feature/hal-router i mq-hal")"
python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['intent']=='create_branch'; assert d['args']==['feature/hal-router']" <<< "$branch_intent"

echo "[6/6] explain intent resolves repo"
explain="$("$ROOT/bin/mq-hal" --no-ai --explain-intent "visa git status i mq-hal")"
echo "$explain" | grep -q "Resolved"
echo "$explain" | grep -q "repo: mq-hal"

echo "OK: hal router smoke test passed"
