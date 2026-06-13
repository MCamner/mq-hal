#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

TMPBIN="$(mktemp -d)"
trap 'rm -rf "$TMPBIN"' EXIT

cat >"$TMPBIN/editor" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'editor:%s\n' "$*" >"$TMPDIR/mq-hal-editor-opened"
SH
chmod +x "$TMPBIN/editor"
export EDITOR="$TMPBIN/editor"

echo "SMOKE: operator actions"

echo "[1/7] syntax"
python3 -m py_compile hal/operator.py

echo "[2/7] next sample"
./bin/mq-hal next --sample | grep -q "Operator Next"
./bin/mq-hal next --sample | grep -q "CHANGELOG missing"
./bin/mq-hal next --sample | grep -q "open CHANGELOG.md"

echo "[3/7] next json"
./bin/mq-hal next --sample --json | python3 -m json.tool >/dev/null

echo "[4/7] fix preview"
./bin/mq-hal fix --sample | grep -q "mqlaunch fix"
./bin/mq-hal fix "CHANGELOG missing" --json | python3 -m json.tool >/dev/null

echo "[5/7] open preview and json"
./bin/mq-hal open CHANGELOG.md --repo mq-hal | grep -q "Preview only"
./bin/mq-hal open CHANGELOG.md --repo mq-hal --json | python3 -m json.tool >/dev/null

echo "[6/7] open confirmed routes to editor"
./bin/mq-hal open CHANGELOG.md --repo mq-hal --confirm >/tmp/mq-hal-open.out
test -f "$TMPDIR/mq-hal-editor-opened"
grep -q "CHANGELOG.md" "$TMPDIR/mq-hal-editor-opened"

echo "[7/7] path guard"
if ./bin/mq-hal open ../outside --repo mq-hal >/tmp/mq-hal-open-bad.out 2>&1; then
  echo "ERROR: open outside repo unexpectedly passed" >&2
  exit 1
fi
grep -q "outside the repo" /tmp/mq-hal-open-bad.out

echo "OK: operator actions smoke passed"
