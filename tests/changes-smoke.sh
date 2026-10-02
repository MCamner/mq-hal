#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export MQ_HAL_STATE_DIR="$WORK/state"

cat >"$WORK/prev.json" <<'JSON'
{
  "schema": "mq_hal.changes_snapshot.v1",
  "taken_at": "2026-10-01T08:00:00+00:00",
  "source": "fixture",
  "checks": [
    {"id": "release:mq-hal", "status": "PASS", "detail": "go", "source": "mq-agent stack release-check"},
    {"id": "runtime:mq-mcp", "status": "FAIL", "detail": "connection refused", "source": "mq-hal runtime"},
    {"id": "stack:repo-signal:contract", "status": "WARN", "detail": "contract=REVIEW", "source": "mq-agent stack cockpit"},
    {"id": "runtime:GitHub", "status": "WARN", "detail": "auth unavailable", "source": "mq-hal runtime"},
    {"id": "runtime:Ollama", "status": "FAIL", "detail": "api down", "source": "mq-hal runtime"}
  ]
}
JSON

cat >"$WORK/cur.json" <<'JSON'
{
  "schema": "mq_hal.changes_snapshot.v1",
  "taken_at": "2026-10-02T08:00:00+00:00",
  "source": "fixture",
  "checks": [
    {"id": "release:mq-hal", "status": "FAIL", "detail": "CHANGELOG missing", "source": "mq-agent stack release-check"},
    {"id": "runtime:mq-mcp", "status": "FAIL", "detail": "connection refused", "source": "mq-hal runtime"},
    {"id": "stack:repo-signal:contract", "status": "PASS", "detail": "contract=READY", "source": "mq-agent stack cockpit"},
    {"id": "runtime:Ollama", "status": "SKIPPED", "detail": "probe skipped", "source": "mq-hal runtime"}
  ]
}
JSON

echo "SMOKE: changes"

echo "[1/6] syntax"
python3 -m py_compile hal/changes.py

echo "[2/6] two snapshots: new, resolved, persisting, unverified"
./bin/mq-hal changes --since "$WORK/prev.json" --current "$WORK/cur.json" --no-save --json \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['schema'] == 'mq_hal.changes.v1', d['schema']
ids = lambda key: sorted(item['id'] for item in d[key])
assert ids('new') == ['release:mq-hal'], d['new']
assert d['new'][0]['previous_status'] == 'PASS' and d['new'][0]['status'] == 'FAIL', d['new']
assert d['new'][0]['source'] == 'mq-agent stack release-check', d['new']
assert ids('resolved') == ['stack:repo-signal:contract'], d['resolved']
assert ids('persisting') == ['runtime:mq-mcp'], d['persisting']
# Missing or skipped data must never count as resolved.
assert ids('unverified') == ['runtime:GitHub', 'runtime:Ollama'], d['unverified']
assert d['previous']['taken_at'] == '2026-10-01T08:00:00+00:00'
assert d['current']['taken_at'] == '2026-10-02T08:00:00+00:00'
assert d['status'] == 'FAIL', d['status']
fb = d['feedback']
assert fb['schema'] == 'mq.feedback.v1'
assert fb['next_action']['command'] == 'mq-hal release blockers', fb
assert fb['next_action']['safety'] == 'read-only', fb
"

echo "[3/6] human output"
out="$(./bin/mq-hal changes --since "$WORK/prev.json" --current "$WORK/cur.json" --no-save)"
grep -q "^NEW" <<<"$out"
grep -q "FAIL  release:mq-hal  PASS -> FAIL" <<<"$out"
grep -q "^RESOLVED" <<<"$out"
grep -q "PASS  stack:repo-signal:contract  WARN -> PASS" <<<"$out"
grep -q "^PERSISTING" <<<"$out"
grep -q "^UNVERIFIED" <<<"$out"
grep -q "mq-hal release blockers" <<<"$out"
test ! -e "$MQ_HAL_STATE_DIR/changes"

echo "[4/6] --since last: baseline, then compare against saved snapshot"
./bin/mq-hal changes --current "$WORK/prev.json" --json \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['previous'] is None, d['previous']
assert d['status'] == 'SKIPPED', d['status']
assert d['new'] == [] and d['resolved'] == [], d
"
test "$(ls "$MQ_HAL_STATE_DIR/changes" | wc -l | tr -d ' ')" = "1"
./bin/mq-hal changes --since last --current "$WORK/cur.json" --json \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert [i['id'] for i in d['new']] == ['release:mq-hal'], d['new']
assert [i['id'] for i in d['resolved']] == ['stack:repo-signal:contract'], d['resolved']
"
test "$(ls "$MQ_HAL_STATE_DIR/changes" | wc -l | tr -d ' ')" = "2"

echo "[5/6] sample works without saving"
rm -rf "$MQ_HAL_STATE_DIR"
./bin/mq-hal changes --sample | grep -q "HAL Changes"
./bin/mq-hal changes --sample --json | python3 -m json.tool >/dev/null
test ! -e "$MQ_HAL_STATE_DIR/changes"

echo "[6/6] bad snapshot is rejected"
echo '{"schema":"other"}' >"$WORK/bad.json"
if ./bin/mq-hal changes --since "$WORK/bad.json" --current "$WORK/cur.json" --no-save >/dev/null 2>&1; then
  echo "FAIL: bad snapshot accepted" >&2
  exit 1
fi

echo "OK: changes smoke passed"
