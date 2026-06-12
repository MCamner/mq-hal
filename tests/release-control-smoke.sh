#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

TMPBIN="$(mktemp -d)"
trap 'rm -rf "$TMPBIN"' EXIT

cat >"$TMPBIN/mq-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == "stack release-check --json" ]]; then
  printf '%s\n' '{"title":"Release Control Center","repos":[{"repo":"mq-hal","version":"1.5.0","ready":true,"score":96,"blockers":[],"gates":[{"name":"VERSION","status":"PASS"},{"name":"smoke","status":"PASS"}]},{"repo":"mqobsidian","version":"0.3.0","ready":false,"score":74,"blockers":["CHANGELOG missing"],"gates":[{"name":"CHANGELOG","status":"FAIL","message":"missing entry"}]}],"overall":{"ready":false,"score":85,"blockers":1}}'
  exit 0
fi
echo "unexpected mq-agent args: $*" >&2
exit 2
SH
chmod +x "$TMPBIN/mq-agent"
export PATH="$TMPBIN:$PATH"

echo "SMOKE: release control"

echo "[1/7] syntax"
python3 -m py_compile hal/release.py

echo "[2/7] release summary"
./bin/mq-hal release | grep -q "Release Control Center"
./bin/mq-hal release | grep -q "mq-hal"
./bin/mq-hal release | grep -q "85/100"

echo "[3/7] release json"
./bin/mq-hal release --json | python3 -m json.tool >/dev/null
./bin/mq-hal release --json | grep -q '"repos"'

echo "[4/7] gates"
./bin/mq-hal release gates | grep -q "Release Gates"
./bin/mq-hal release gates | grep -q "VERSION"

echo "[5/7] blockers"
./bin/mq-hal release blockers | grep -q "Release Blockers"
./bin/mq-hal release blockers | grep -q "CHANGELOG missing"

echo "[6/7] sample"
./bin/mq-hal release --sample | grep -q "Release Control Center"
./bin/mq-hal release blockers --sample | grep -q "CHANGELOG missing"

echo "[7/7] release-brief remains available"
./bin/mq-hal release-brief --sample | grep -q "HAL Release Brief"

echo "OK: release control smoke test passed"
