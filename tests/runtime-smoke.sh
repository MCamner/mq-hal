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

echo "[1/6] syntax"
python3 -m py_compile hal/runtime.py

echo "[2/6] sample text"
./bin/mq-hal runtime --sample | grep -q "MQ Runtime"
./bin/mq-hal runtime --sample | grep -q "Ollama"
./bin/mq-hal runtime --sample | grep -q "mq-mcp"
./bin/mq-hal runtime --sample | grep -q "GitHub"
./bin/mq-hal runtime --sample | grep -q "brain"

echo "[3/6] sample json"
./bin/mq-hal runtime --sample --json | python3 -m json.tool >/dev/null
./bin/mq-hal runtime --sample --json | grep -q '"services"'

echo "[4/6] services details"
./bin/mq-hal runtime services --sample | grep -q "tools"
./bin/mq-hal runtime services --sample | grep -q "vault"

echo "[5/6] live json shape"
./bin/mq-hal runtime --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['title'] == 'MQ Runtime'
services = {item['name']: item for item in d['services']}
for name in ['Ollama', 'mq-mcp', 'GitHub', 'brain']:
    assert name in services, name
    assert services[name]['status'] in {'RUNNING', 'WARN', 'DOWN'}
assert 'overall' in d and d['overall']['status'] in {'RUNNING', 'WARN', 'DOWN'}
"

echo "[6/6] brain health can run"
./bin/mq-hal runtime --json | grep -q '"brain"'

echo "OK: runtime control smoke passed"
