#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

TMPBIN="$(mktemp -d)"
BRAIN_DIR="$(mktemp -d)"
trap 'rm -rf "$TMPBIN" "$BRAIN_DIR"' EXIT

mkdir -p "$BRAIN_DIR/memory" "$BRAIN_DIR/learn" "$BRAIN_DIR/truth" "$BRAIN_DIR/reviews"

cat >"$TMPBIN/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == "auth status" ]]; then
  echo "Logged in to github.com"
  exit 0
fi
echo "unexpected gh args: $*" >&2
exit 2
SH
chmod +x "$TMPBIN/gh"

export PATH="$TMPBIN:$PATH"
export MQ_HAL_BRAIN_ROOT="$BRAIN_DIR"

echo "SMOKE: runtime control"

echo "[1/7] syntax"
python3 -m py_compile hal/runtime.py

echo "[2/7] sample text"
./bin/mq-hal runtime --sample | grep -q "MQ Runtime"
./bin/mq-hal runtime --sample | grep -q "Ollama"
./bin/mq-hal runtime --sample | grep -q "mq-mcp"
./bin/mq-hal runtime --sample | grep -q "GitHub"
./bin/mq-hal runtime --sample | grep -q "brain"

echo "[3/7] sample json"
./bin/mq-hal runtime --sample --json | python3 -m json.tool >/dev/null
./bin/mq-hal runtime --sample --json | grep -q '"services"'

echo "[4/7] services details"
./bin/mq-hal runtime services --sample | grep -q "tools"
./bin/mq-hal runtime services --sample | grep -q "vault"

echo "[5/7] live json shape"
./bin/mq-hal runtime --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['title'] == 'MQ Runtime'
services = {item['name']: item for item in d['services']}
for name in ['Ollama', 'mq-mcp', 'GitHub', 'brain']:
    assert name in services, name
    assert services[name]['status'] in {'PASS', 'WARN', 'FAIL', 'SKIPPED', 'UNAVAILABLE'}
assert 'overall' in d and d['overall']['status'] in {'PASS', 'WARN', 'FAIL', 'SKIPPED', 'UNAVAILABLE'}
"

echo "[6/7] brain health can run"
./bin/mq-hal runtime --json | grep -q '"brain"'

echo "[7/7] truth exports are found where mq-agent writes them"
# mq-agent writes stack truth to memory/stack-truth/. The vault has no
# top-level truth/ folder, so probing for one reported "missing: truth"
# against a perfectly healthy vault.
VAULT="$(mktemp -d)"
trap 'rm -rf "$VAULT"' EXIT
mkdir -p "$VAULT/memory/stack-truth" "$VAULT/learn" "$VAULT/reviews"
printf '# truth\n' > "$VAULT/memory/stack-truth/2026-08-06-mq-stack-truth.md"

MQ_HAL_BRAIN_ROOT="$VAULT" ./bin/mq-hal runtime --json | python3 -c "
import json, sys
brain = {item['name']: item for item in json.load(sys.stdin)['services']}['brain']
detail = json.dumps(brain)
assert 'missing: truth' not in detail, f'truth export folder not found: {detail}'
assert brain['status'] == 'PASS', f'healthy vault reported {brain[\"status\"]}: {detail}'
"

echo "OK: runtime control smoke passed"
