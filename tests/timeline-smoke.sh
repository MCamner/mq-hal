#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_STATE="$(mktemp -d)"

export MQ_HAL_STATE_DIR="$TMP_STATE"

echo "SMOKE: mq-hal timeline"

echo "[1/5] syntax check"
python3 -m py_compile "$ROOT/scripts/timeline.py"

echo "[2/5] empty timeline works"
"$ROOT/bin/mq-hal" timeline >/tmp/mq-hal-timeline-empty.txt
grep -q "HAL Timeline" /tmp/mq-hal-timeline-empty.txt

echo "[3/5] create note"
"$ROOT/bin/mq-hal" remember "timeline smoke note" --repo sample >/tmp/mq-hal-timeline-note.txt

echo "[4/5] timeline shows note"
"$ROOT/bin/mq-hal" timeline >/tmp/mq-hal-timeline.txt
grep -q "timeline smoke note" /tmp/mq-hal-timeline.txt

echo "[5/5] json mode works"
"$ROOT/bin/mq-hal" timeline --json >/tmp/mq-hal-timeline.json
python3 -m json.tool /tmp/mq-hal-timeline.json >/dev/null

echo "OK: timeline smoke test passed"
