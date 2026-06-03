#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_STATE="$(mktemp -d)"

export MQ_HAL_STATE_DIR="$TMP_STATE"
export MQ_HAL_DISABLE_MEMORY=1

echo "SMOKE: release-brief"

echo "[1/6] syntax check"
python3 -m py_compile "$ROOT/scripts/release_brief.py"

echo "[2/6] sample text works"
"$ROOT/bin/mq-hal" release-brief --sample >/tmp/mq-hal-release-brief.txt
grep -q "HAL Release Brief" /tmp/mq-hal-release-brief.txt
grep -q "Overall:" /tmp/mq-hal-release-brief.txt

echo "[3/6] sample JSON works"
"$ROOT/bin/mq-hal" release-brief --sample --json >/tmp/mq-hal-release-brief.json
python3 -m json.tool /tmp/mq-hal-release-brief.json >/dev/null

echo "[4/6] GitHub release check uses supported gh JSON fields"
! grep -q "isLatest" "$ROOT/scripts/release_brief.py"

echo "[5/6] skip flags parse"
"$ROOT/bin/mq-hal" release-brief --sample --skip-gh --skip-doctor --skip-release-check >/tmp/mq-hal-release-brief-skip.txt
grep -q "HAL Release Brief" /tmp/mq-hal-release-brief-skip.txt

echo "[6/6] command is routed through bin wrapper"
"$ROOT/bin/mq-hal" release --sample >/tmp/mq-hal-release-alias.txt
grep -q "HAL Release Brief" /tmp/mq-hal-release-alias.txt

echo "OK: release-brief smoke test passed"
