#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_STATE="$(mktemp -d)"

export MQ_HAL_STATE_DIR="$TMP_STATE"

echo "SMOKE: mq-hal session memory"

echo "[1/5] syntax check"
python3 -m py_compile "$ROOT/scripts/session_memory.py"

echo "[2/5] empty session works"
"$ROOT/bin/mq-hal" session >/tmp/mq-hal-session-empty.txt
grep -q "HAL Session Memory" /tmp/mq-hal-session-empty.txt

echo "[3/5] remember works"
"$ROOT/bin/mq-hal" remember "test note" --repo sample >/tmp/mq-hal-session-note.txt
grep -q "Saved note" /tmp/mq-hal-session-note.txt

echo "[4/5] last works"
"$ROOT/bin/mq-hal" last >/tmp/mq-hal-session-last.txt
grep -q "test note" /tmp/mq-hal-session-last.txt

echo "[5/5] json works"
"$ROOT/bin/mq-hal" session --json >/tmp/mq-hal-session.json
python3 -m json.tool /tmp/mq-hal-session.json >/dev/null

echo "OK: session memory smoke test passed"
