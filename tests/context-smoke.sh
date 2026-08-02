#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

OBS_DIR="$(mktemp -d)"
EMPTY_DIR="$(mktemp -d)/missing-vault"
trap 'rm -rf "$OBS_DIR" "$(dirname "$EMPTY_DIR")"' EXIT

# Avoid an ambient MQOBSIDIAN_PATH leaking into the test.
unset MQOBSIDIAN_PATH

echo "SMOKE: context"

echo "[1/9] syntax"
python3 -m py_compile hal/context.py

echo "[2/9] missing mqobsidian returns UNAVAILABLE (not FAIL)"
./bin/mq-hal context --root "$EMPTY_DIR" --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['schema'] == 'mq_hal.context_status.v1', d['schema']
assert d['status'] == 'UNAVAILABLE', d['status']
assert d['checks']['repo_found'] is False
assert d['latest_task_pack'] is None
assert d['token_budget']['status'] == 'UNAVAILABLE'
"
./bin/mq-hal context --root "$EMPTY_DIR" | grep -q "mqobsidian:.*missing"

# Build the mqobsidian context scaffold.
mkdir -p "$OBS_DIR/docs" "$OBS_DIR/schemas" "$OBS_DIR/templates" \
         "$OBS_DIR/examples" "$OBS_DIR/scripts"
printf '%s\n' "# context budget" >"$OBS_DIR/docs/context-budget.md"
printf '%s\n' "# roadmap" >"$OBS_DIR/docs/roadmap-token-reduction.md"
printf '%s\n' '{"title":"context-pack.v1"}' >"$OBS_DIR/schemas/context-pack.v1.json"
printf '%s\n' "# template" >"$OBS_DIR/templates/context-pack.md"
printf '%s\n' "# example" >"$OBS_DIR/examples/sanitized-context-pack.md"
cat >"$OBS_DIR/scripts/check-token-budget.py" <<'PY'
#!/usr/bin/env python3
import sys
print("token budget checks passed")
sys.exit(0)
PY

echo "[3/9] scaffold without task pack returns WARN"
./bin/mq-hal context --root "$OBS_DIR" --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['status'] == 'WARN', d['status']
assert d['checks']['repo_found'] is True
assert d['checks']['context_pack_schema'] is True
assert d['checks']['latest_task_pack'] is False
assert d['token_budget']['status'] == 'PASS', d['token_budget']
"
./bin/mq-hal context --root "$OBS_DIR" latest-pack | grep -q "latest task-pack: missing"

# Add a generated task pack.
mkdir -p "$OBS_DIR/.mq/context"
cat >"$OBS_DIR/.mq/context/task-pack.md" <<'MD'
---
schema: context-pack.v1
target: codex
task: smoke test pack
generated_at: 2026-06-17T00:00:00Z
repo: mq-hal
summary: smoke
---

# Task Context Pack
MD

echo "[4/9] scaffold with task pack returns PASS"
./bin/mq-hal context --root "$OBS_DIR" --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['status'] == 'PASS', d['status']
assert d['latest_task_pack'] == '.mq/context/task-pack.md', d['latest_task_pack']
assert d['target_readiness'] == 'codex', d['target_readiness']
"

echo "[5/9] status text view"
./bin/mq-hal context --root "$OBS_DIR" status | grep -q "Context Pack Status"
./bin/mq-hal context --root "$OBS_DIR" status | grep -q "token budget:.*pass"
./bin/mq-hal context --root "$OBS_DIR" status | grep -q "target readiness:.*codex"

echo "[6/9] latest-pack view"
./bin/mq-hal context --root "$OBS_DIR" latest-pack | grep -q ".mq/context/task-pack.md"
./bin/mq-hal context --root "$OBS_DIR" latest-pack | grep -q "target: codex"

echo "[7/9] budget delegates to check-token-budget.py"
./bin/mq-hal context --root "$OBS_DIR" budget | grep -q "status:  pass"
./bin/mq-hal context --root "$OBS_DIR" budget | grep -q "python3 scripts/check-token-budget.py"

echo "[8/9] budget handles missing script safely"
rm -f "$OBS_DIR/scripts/check-token-budget.py"
./bin/mq-hal context --root "$OBS_DIR" budget --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['token_budget']['status'] == 'UNAVAILABLE', d['token_budget']
"
./bin/mq-hal context --root "$OBS_DIR" budget | grep -q "status:  unavailable"

echo "[9/9] open only previews files inside mqobsidian path"
./bin/mq-hal context --root "$OBS_DIR" open ".mq/context/task-pack.md" | grep -q "schema: context-pack.v1"
# Out-of-root open is refused and exits non-zero; capture so pipefail does not abort.
REJECT_JSON="$(./bin/mq-hal context --root "$OBS_DIR" open "../../../etc/passwd" --json || true)"
printf '%s' "$REJECT_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['status'] == 'rejected', d['status']
assert d['returncode'] == 2, d['returncode']
"
if ./bin/mq-hal context --root "$OBS_DIR" open "../../../etc/passwd" >/dev/null 2>&1; then
  echo "ERROR: out-of-root open should fail" >&2
  exit 1
fi

echo "OK: context smoke passed"
