#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

export MQ_HAL_STATE_DIR="$WORK/state"
# config/repos.json maps mq-hal to ~/mq-hal; CI checks out elsewhere.
mkdir -p "$WORK/home"
ln -s "$ROOT" "$WORK/home/mq-hal"
export HOME="$WORK/home"
export PYTHONPYCACHEPREFIX="$WORK/pycache"
LEDGER="$MQ_HAL_STATE_DIR/actions.jsonl"

count() { [[ -f "$LEDGER" ]] && wc -l <"$LEDGER" | tr -d ' ' || echo 0; }
last() { tail -n 1 "$LEDGER"; }

echo "SMOKE: action ledger"

echo "[1/13] syntax check"
python3 -m py_compile "$ROOT/scripts/action_log.py"

echo "[2/13] empty ledger is not an error"
"$ROOT/bin/mq-hal" actions | grep -q "No recorded actions"
"$ROOT/bin/mq-hal" actions --json | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['schema']=='mq_hal.actions.v1'; assert d['actions']==[]"

echo "[3/13] raw intent does not record"
"$ROOT/bin/mq-hal" --no-ai --raw-intent "visa git status i mq-hal" >/dev/null
[[ "$(count)" == "0" ]]

echo "[4/13] executed router command records one entry"
"$ROOT/bin/mq-hal" --no-ai "visa git status i mq-hal" >/dev/null
[[ "$(count)" == "1" ]]
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['schema'] == 'mq_hal.action.v1', d
assert d['source'] == 'router' and d['routing'] == 'deterministic', d
assert d['intent'] == 'git_status' and d['repo'] == 'mq-hal', d
assert d['command'] == ['git', 'status', '--short'], d
assert d['confirmation'] == 'not_required' and d['outcome'] == 'executed', d
assert d['exit_code'] == 0 and isinstance(d['duration_ms'], int), d
"

echo "[5/13] cancelled confirmation records cancelled"
set +e
echo n | "$ROOT/bin/mq-hal" --no-ai --confirm "visa git status i mq-hal" >/dev/null
code=$?
set -e
[[ "$code" == "130" ]]
[[ "$(count)" == "2" ]]
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['confirmation'] == 'cancelled' and d['outcome'] == 'cancelled', d
assert d['exit_code'] == 130, d
"

echo "[6/13] router refusal records refused"
set +e
"$ROOT/bin/mq-hal" --no-ai "skapa branch bad..name i mq-hal" >/dev/null 2>&1
set -e
[[ "$(count)" == "3" ]]
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['intent'] == 'create_branch' and d['outcome'] == 'refused', d
assert d['command'] is None and d['exit_code'] == 2, d
"

echo "[7/13] missing command records exit 127"
set +e
VISUAL=/nonexistent/mq-hal-editor "$ROOT/bin/mq-hal" --no-ai "öppna README.md i mq-hal" >/dev/null 2>&1
code=$?
set -e
[[ "$code" == "127" ]]
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['intent'] == 'open_editor' and d['outcome'] == 'executed', d
assert d['exit_code'] == 127, d
"

echo "[8/13] secrets in prompts are redacted"
"$ROOT/bin/mq-hal" --no-ai "hitta token=hunter2secret i mq-hal" </dev/null >/dev/null 2>&1 || true
if grep -q "hunter2secret" "$LEDGER"; then echo "FAIL: secret leaked into ledger" >&2; exit 1; fi
last | grep -q "REDACTED"
"$ROOT/bin/mq-hal" actions --json --outcome executed | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['count'] >= 2 and all(a['outcome'] == 'executed' for a in d['actions']), d
"
"$ROOT/bin/mq-hal" actions --last 2 | grep -q "Recorded actions"

echo "[9/13] execute records each step"
cat >"$WORK/plan.json" <<'JSON'
{"goal": "ledger smoke", "risk": "low", "affected_repos": ["mq-hal"],
 "steps": [
   {"id": 1, "description": "status", "safe_command": "git status --short"},
   {"id": 2, "description": "bad", "safe_command": "git status; rm -rf x"}
 ]}
JSON
"$ROOT/bin/mq-hal" execute "$WORK/plan.json" --confirm --skip-critic </dev/null >/dev/null 2>&1 || true
"$ROOT/bin/mq-hal" actions --json --source execute | python3 -c "
import json, sys
d = json.load(sys.stdin)
outcomes = [(a['intent'], a['outcome'], a['exit_code']) for a in d['actions']]
assert outcomes == [('step 1', 'executed', 0), ('step 2', 'refused', 2)], outcomes
"

echo "[10/13] confirmed open records the editor command"
VISUAL=true "$ROOT/bin/mq-hal" open README.md --repo mq-hal --confirm >/dev/null
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['source'] == 'open' and d['repo'] == 'mq-hal', d
assert d['command'][0] == 'true' and d['exit_code'] == 0, d
"

echo "[11/13] grep does not wait on an open stdin"
set +e
sleep 30 | timeout 15 "$ROOT/bin/mq-hal" --no-ai "hitta ROADMAP i mq-hal" >/dev/null 2>&1
code=$?
set -e
[[ "$code" != "124" ]] || { echo "FAIL: grep intent hung on stdin" >&2; exit 1; }

echo "[12/13] confirmed open with a missing editor records exit 127"
set +e
VISUAL=/nonexistent/mq-hal-editor "$ROOT/bin/mq-hal" open README.md --repo mq-hal --confirm >/dev/null 2>"$WORK/open-err"
code=$?
set -e
[[ "$code" == "127" ]] || { echo "FAIL: expected 127, got $code" >&2; cat "$WORK/open-err" >&2; exit 1; }
if grep -q Traceback "$WORK/open-err"; then echo "FAIL: open crashed" >&2; exit 1; fi
last | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert d['source'] == 'open' and d['exit_code'] == 127, d
"

echo "[13/13] unwritable ledger still runs the command"
export MQ_HAL_STATE_DIR="$WORK/broken"
mkdir -p "$MQ_HAL_STATE_DIR/actions.jsonl"
"$ROOT/bin/mq-hal" --no-ai "visa git status i mq-hal" >/dev/null 2>"$WORK/err"
grep -q "WARN: action ledger not written" "$WORK/err"

echo "OK: action ledger smoke test passed"
