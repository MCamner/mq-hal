#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

STATE_DIR="$(mktemp -d)"
BRAIN_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR" "$BRAIN_DIR"' EXIT

mkdir -p "$BRAIN_DIR/memory" "$BRAIN_DIR/learn" "$BRAIN_DIR/truth" "$BRAIN_DIR/reviews" "$STATE_DIR/learn"
printf '%s\n' "# Note" "brain release note" >"$BRAIN_DIR/memory/note.md"
printf '%s\n' '{"export":"learn"}' >"$BRAIN_DIR/learn/export.jsonl"
printf '%s\n' "# Latest release" >"$BRAIN_DIR/truth/latest-release.md"
printf '%s\n' "# Review" "release blocker clear" >"$BRAIN_DIR/reviews/review.md"
printf '%s\n' '{"lesson":"brain command"}' >"$STATE_DIR/learn/lessons.jsonl"

export MQ_HAL_STATE_DIR="$STATE_DIR"
export MQOBSIDIAN_PATH="$BRAIN_DIR"

echo "SMOKE: brain"

echo "[1/7] syntax"
python3 -m py_compile hal/brain.py

echo "[2/7] summary output"
./bin/mq-hal brain | grep -q "Brain Control Center"
./bin/mq-hal brain | grep -q "brain notes"
./bin/mq-hal brain | grep -q "Latest release"

echo "[3/7] health output"
./bin/mq-hal brain health | grep -q "Brain Health"
./bin/mq-hal brain health | grep -q "memory"

echo "[4/7] recent output"
./bin/mq-hal brain recent | grep -q "Brain Recent"
./bin/mq-hal brain recent | grep -q "latest-release.md"

echo "[5/7] search output"
./bin/mq-hal brain search release | grep -q "Brain Search"
./bin/mq-hal brain search release | grep -q "latest-release.md"

echo "[6/7] json output"
./bin/mq-hal brain --json | python3 -m json.tool >/dev/null
./bin/mq-hal brain search release --json | python3 -m json.tool >/dev/null

echo "[7/7] sample output"
./bin/mq-hal brain --sample | grep -q "Brain Control Center"

echo "OK: brain smoke test passed"
