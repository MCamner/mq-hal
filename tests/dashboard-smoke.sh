#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: dashboard"

echo "[1/7] syntax"
python3 -m py_compile hal/dashboard.py

echo "[2/7] dashboard home"
./bin/mq-hal dashboard --sample --once --no-clear > /tmp/mq-hal-dashboard-home.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-home.out
grep -q "1 Stack" /tmp/mq-hal-dashboard-home.out
grep -q "4 Runtime" /tmp/mq-hal-dashboard-home.out
grep -q "6 Context" /tmp/mq-hal-dashboard-home.out

echo "[3/7] json"
./bin/mq-hal dashboard --sample --json | python3 -m json.tool >/dev/null
./bin/mq-hal dashboard --sample --json | grep -q '"alerts"'

echo "[4/7] navigation"
printf '1\n2\n3\n4\n5\n6\na\nq\n' | ./bin/mq-hal dashboard --sample --no-clear > /tmp/mq-hal-dashboard.out
grep -q "MQ Stack" /tmp/mq-hal-dashboard.out
grep -q "Brain" /tmp/mq-hal-dashboard.out
grep -q "Release Control Center" /tmp/mq-hal-dashboard.out
grep -q "MQ Runtime" /tmp/mq-hal-dashboard.out
grep -q "History" /tmp/mq-hal-dashboard.out
grep -q "Context Pack Status" /tmp/mq-hal-dashboard.out
grep -q "Alerts" /tmp/mq-hal-dashboard.out

echo "[5/7] refresh"
printf 'r\nq\n' | ./bin/mq-hal dashboard --sample --no-clear > /tmp/mq-hal-dashboard-refresh.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-refresh.out

echo "[6/7] no-args opens dashboard"
printf 'q\n' | ./bin/mq-hal > /tmp/mq-hal-dashboard-noargs.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-noargs.out

echo "[7/7] command docs mention dashboard"
grep -q "\`dashboard\`" docs/COMMAND_SURFACE.md

echo "OK: dashboard smoke passed"
