#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

AGENT_DIR="$(mktemp -d)"
BRAIN_DIR="$(mktemp -d)"
trap 'rm -rf "$AGENT_DIR" "$BRAIN_DIR"' EXIT

mkdir -p "$BRAIN_DIR/memory" "$BRAIN_DIR/learn" "$BRAIN_DIR/truth" "$BRAIN_DIR/reviews"

cat >"$AGENT_DIR/stack-history.jsonl" <<'JSONL'
{"timestamp":"2026-06-11T10:00:00","overall":{"score":88}}
{"timestamp":"2026-06-12T10:00:00","score":92}
JSONL

cat >"$BRAIN_DIR/memory/note.md" <<'MD'
# Note
MD
cat >"$BRAIN_DIR/truth/latest-release.md" <<'MD'
# Release
MD

export MQ_AGENT_STATE_DIR="$AGENT_DIR"
export MQ_HAL_BRAIN_ROOT="$BRAIN_DIR"

echo "SMOKE: history"

echo "[1/7] syntax"
python3 -m py_compile hal/history.py

echo "[2/7] sample history"
./bin/mq-hal history --sample | grep -q "HAL History"
./bin/mq-hal history --sample | grep -q "Stack score"
./bin/mq-hal history --sample | grep -q "Brain growth"

echo "[3/7] sample json"
./bin/mq-hal history --sample --json | python3 -m json.tool >/dev/null

echo "[4/7] live history from temp sources"
./bin/mq-hal history > /tmp/mq-hal-history.out
grep -q "92/100" /tmp/mq-hal-history.out
grep -q "latest-release.md" /tmp/mq-hal-history.out

echo "[5/7] live json shape"
./bin/mq-hal history --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for key in ['stack_score', 'brain_growth', 'release_history']:
    assert key in d, key
assert d['stack_score'][-1]['score'] == 92
assert d['release_history'], 'missing release history'
"

echo "[6/7] alerts"
./bin/mq-hal alerts --sample | grep -q "HAL Alerts"
./bin/mq-hal alerts --sample --json | python3 -m json.tool >/dev/null

echo "[7/7] command docs mention history and alerts"
grep -q "\`history\`" docs/COMMAND_SURFACE.md
grep -q "\`alerts\`" docs/COMMAND_SURFACE.md

echo "OK: history smoke passed"
