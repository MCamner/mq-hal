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

cat >"$TMPBIN/mqlaunch" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'mqlaunch:%s\n' "$*"
SH
chmod +x "$TMPBIN/mqlaunch"
export PATH="$TMPBIN:$PATH"

echo "SMOKE: operator actions"

echo "[1/8] syntax"
python3 -m py_compile hal/operator.py

echo "[2/8] next sample"
./bin/mq-hal next --sample | grep -q "Operator Next"
./bin/mq-hal next --sample | grep -q "CHANGELOG missing"
./bin/mq-hal next --sample | grep -q "open CHANGELOG.md"

echo "[3/8] next json"
./bin/mq-hal next --sample --json | python3 -m json.tool >/dev/null

echo "[4/8] fix preview"
./bin/mq-hal fix --sample | grep -q "mqlaunch fix"
./bin/mq-hal fix "CHANGELOG missing" --json | python3 -m json.tool >/dev/null

echo "[5/8] open preview and json"
./bin/mq-hal open CHANGELOG.md --repo mq-hal | grep -q "Preview only"
./bin/mq-hal open CHANGELOG.md --repo mq-hal --json | python3 -m json.tool >/dev/null

echo "[6/8] confirmed actions report completion"
./bin/mq-hal open CHANGELOG.md --repo mq-hal --confirm >/tmp/mq-hal-open.out
test -f "$TMPDIR/mq-hal-editor-opened"
grep -q "CHANGELOG.md" "$TMPDIR/mq-hal-editor-opened"
grep -q "DONE: opened CHANGELOG.md in mq-hal" /tmp/mq-hal-open.out
./bin/mq-hal fix "CHANGELOG missing" --confirm >/tmp/mq-hal-fix.out
grep -q "DONE: routed fix through mqlaunch" /tmp/mq-hal-fix.out

echo "[7/8] failed action reports exit status"
cat >"$TMPBIN/mqlaunch" <<'SH'
#!/usr/bin/env bash
exit 9
SH
chmod +x "$TMPBIN/mqlaunch"
if ./bin/mq-hal fix "broken" --confirm >/tmp/mq-hal-fix-failed.out 2>&1; then
  echo "ERROR: failed mqlaunch unexpectedly passed" >&2
  exit 1
fi
grep -q "ERROR: mqlaunch fix exited with status 9" /tmp/mq-hal-fix-failed.out

echo "[8/8] path guard"
if ./bin/mq-hal open ../outside --repo mq-hal >/tmp/mq-hal-open-bad.out 2>&1; then
  echo "ERROR: open outside repo unexpectedly passed" >&2
  exit 1
fi
grep -q "outside the repo" /tmp/mq-hal-open-bad.out

echo "OK: operator actions smoke passed"
