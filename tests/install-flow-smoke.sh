#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

echo "SMOKE: install flow"

echo "[1/8] syntax checks"
python3 -m py_compile "$ROOT/scripts/version.py"
python3 -m py_compile "$ROOT/scripts/config_check.py"
python3 -m py_compile "$ROOT/scripts/update.py"
bash -n "$ROOT/install.sh"
bash -n "$ROOT/uninstall.sh"
bash -n "$ROOT/upgrade.sh"

echo "[2/8] version works"
"$ROOT/bin/mq-hal" version >/dev/null
"$ROOT/bin/mq-hal" version --json | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"]'

echo "[3/8] config-check works"
"$ROOT/bin/mq-hal" config-check >/dev/null
"$ROOT/bin/mq-hal" config-check --json | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] in {"ok","fail"}'

echo "[4/8] update dry-run works"
"$ROOT/bin/mq-hal" update >/dev/null
"$ROOT/bin/mq-hal" update --json | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "dry-run"'

echo "[5/8] install creates symlink"
MQ_HAL_PREFIX="$TMP_HOME/bin" "$ROOT/install.sh" >/dev/null
test -L "$TMP_HOME/bin/mq-hal"

echo "[6/8] installed command works"
"$TMP_HOME/bin/mq-hal" version >/dev/null

echo "[7/8] uninstall removes symlink"
MQ_HAL_PREFIX="$TMP_HOME/bin" "$ROOT/uninstall.sh" >/dev/null
test ! -e "$TMP_HOME/bin/mq-hal"

echo "[8/8] install docs exist"
test -f "$ROOT/docs/INSTALL.md"

echo "OK: install flow smoke passed"
