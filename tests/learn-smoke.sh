#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

LEARN="python3 $ROOT/scripts/learn.py"

echo "SMOKE: mq-hal learn"

echo "[1/8] syntax check"
python3 -m py_compile "$ROOT/scripts/learn.py"
echo "  syntax: OK"

echo "[2/8] learn add works"
$LEARN add \
  --repo mq-hal \
  --source manual \
  --task "version sync before release" \
  --lesson "Update README, CHANGELOG and docs/index.html together." \
  --validation "release-check --dry-run passes" >/dev/null
echo "  learn add: OK"

echo "[3/8] learn list shows added lesson"
output=$($LEARN list)
echo "$output" | grep -q "version sync" || {
  echo "ERROR: learn list did not show added lesson" >&2; exit 1
}
echo "  learn list: OK"

echo "[4/8] learn search finds lesson"
output=$($LEARN search "README")
echo "$output" | grep -q "version sync" || {
  echo "ERROR: learn search did not find lesson" >&2; exit 1
}
echo "  learn search: OK"

echo "[5/8] learn show works"
id=$($LEARN list --json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
$LEARN show "$id" | grep -q "Task" || {
  echo "ERROR: learn show did not produce expected output" >&2; exit 1
}
echo "  learn show: OK"

echo "[6/8] learn summarize works"
output=$($LEARN summarize)
echo "$output" | grep -q "Total lessons" || {
  echo "ERROR: learn summarize missing expected output" >&2; exit 1
}
echo "  learn summarize: OK"

echo "[7/8] secret redaction works"
$LEARN add \
  --source claude \
  --task "secret test" \
  --lesson "api_key: sk-abc1234567890123456789012345678901234567890 was found" \
  >/dev/null
lesson=$($LEARN search "secret test" --json | python3 -c "
import sys, json
lessons = json.load(sys.stdin)
print(lessons[0]['lesson'])
")
echo "$lesson" | grep -q "\[REDACTED\]" || {
  echo "ERROR: secret was not redacted in lesson" >&2; exit 1
}
echo "$lesson" | grep -q "sk-abc" && {
  echo "ERROR: raw secret still present after redaction" >&2; exit 1
}
echo "  secret redaction: OK"

echo "[8/8] learn JSON output is valid"
$LEARN list --json | python3 -c "import sys, json; json.load(sys.stdin)" || {
  echo "ERROR: learn list --json is not valid JSON" >&2; exit 1
}
$LEARN summarize --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'total' in d and 'by_source' in d and 'by_repo' in d
" || {
  echo "ERROR: learn summarize --json missing expected keys" >&2; exit 1
}
echo "  JSON output: OK"

echo "OK: learn smoke test passed"
