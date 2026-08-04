#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: dashboard"

echo "[1/8] syntax"
python3 -m py_compile hal/dashboard.py

echo "[2/8] dashboard home"
./bin/mq-hal dashboard --sample --once --no-clear > /tmp/mq-hal-dashboard-home.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-home.out
grep -q "1 Stack" /tmp/mq-hal-dashboard-home.out
grep -q "4 Runtime" /tmp/mq-hal-dashboard-home.out
grep -q "6 Context" /tmp/mq-hal-dashboard-home.out
grep -q "7 Routing" /tmp/mq-hal-dashboard-home.out
grep -q "Status: ready" /tmp/mq-hal-dashboard-home.out

echo "[3/8] json"
./bin/mq-hal dashboard --sample --json | python3 -m json.tool >/dev/null
./bin/mq-hal dashboard --sample --json | grep -q '"alerts"'

echo "[4/8] navigation"
printf '1\n2\n3\n4\n5\n6\n7\na\nq\n' | ./bin/mq-hal dashboard --sample --no-clear > /tmp/mq-hal-dashboard.out
grep -q "MQ Stack" /tmp/mq-hal-dashboard.out
grep -q "Brain" /tmp/mq-hal-dashboard.out
grep -q "Release Control Center" /tmp/mq-hal-dashboard.out
grep -q "MQ Runtime" /tmp/mq-hal-dashboard.out
grep -q "History" /tmp/mq-hal-dashboard.out
grep -q "Context Pack Status" /tmp/mq-hal-dashboard.out
grep -q "MQ Model Routing" /tmp/mq-hal-dashboard.out
grep -q "Alerts" /tmp/mq-hal-dashboard.out
grep -q "Opened Stack." /tmp/mq-hal-dashboard.out

echo "[5/8] refresh feedback"
printf 'r\nq\n' | ./bin/mq-hal dashboard --sample --no-clear > /tmp/mq-hal-dashboard-refresh.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-refresh.out
grep -q "Dashboard refreshed." /tmp/mq-hal-dashboard-refresh.out

echo "[6/8] back and invalid-choice feedback"
printf '1\nb\nwat\nq\n' | ./bin/mq-hal dashboard --sample --no-clear > /tmp/mq-hal-dashboard-feedback.out
grep -q "Back to dashboard." /tmp/mq-hal-dashboard-feedback.out
grep -q "Unknown choice 'wat'" /tmp/mq-hal-dashboard-feedback.out
grep -q "Dashboard closed." /tmp/mq-hal-dashboard-feedback.out

echo "[7/8] no-args opens dashboard"
printf 'q\n' | ./bin/mq-hal > /tmp/mq-hal-dashboard-noargs.out
grep -q "HAL Operator Dashboard" /tmp/mq-hal-dashboard-noargs.out

echo "[8/8] command docs mention dashboard"
grep -q "\`dashboard\`" docs/COMMAND_SURFACE.md

echo "OK: dashboard smoke passed"
