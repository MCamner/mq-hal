#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: mq-hal doctor-summary"

echo "[1/3] syntax check"
python3 -m py_compile "$ROOT/scripts/doctor_summary.py"

echo "[2/3] sample fallback summary works"
"$ROOT/bin/mq-hal" doctor-summary --sample --no-ai >/tmp/mq-hal-doctor-summary.txt

grep -q "HAL Doctor Summary" /tmp/mq-hal-doctor-summary.txt
grep -q "Status:" /tmp/mq-hal-doctor-summary.txt

echo "[3/3] sample JSON summary works"
"$ROOT/bin/mq-hal" doctor-summary --sample --no-ai --json >/tmp/mq-hal-doctor-summary.json
python3 -m json.tool /tmp/mq-hal-doctor-summary.json >/dev/null

echo "OK: doctor-summary smoke test passed"
