#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_STATE="$(mktemp -d)"

export MQ_HAL_STATE_DIR="$TMP_STATE"
export MQ_HAL_DISABLE_MEMORY=1

echo "SMOKE: audit"

echo "[1/4] syntax check"
python3 -m py_compile "$ROOT/scripts/audit.py"

echo "[2/4] sample text works"
"$ROOT/bin/mq-hal" audit --sample >/tmp/mq-hal-audit.txt
grep -q "HAL Audit" /tmp/mq-hal-audit.txt
grep -q "Publish readiness:" /tmp/mq-hal-audit.txt
grep -q "README score:" /tmp/mq-hal-audit.txt
grep -q "Recommendation" /tmp/mq-hal-audit.txt

echo "[3/4] sample JSON works"
"$ROOT/bin/mq-hal" audit --sample --json >/tmp/mq-hal-audit.json
python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
assert 'repo' in d
assert 'overall' in d
assert 'publish' in d
assert 'readme' in d
assert 'recommendation' in d
assert isinstance(d['publish']['checks'], list)
assert isinstance(d['readme']['missing'], list)
" </dev/null </tmp/mq-hal-audit.json

echo "[4/4] routed through bin wrapper"
"$ROOT/bin/mq-hal" audit --sample | grep -q "HAL Audit"

echo "OK: audit smoke test passed"
