#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="$ROOT/README.md"
INTEGRATION="$ROOT/docs/INTEGRATION.md"

echo "SMOKE: docs"

echo "[1/9] README exists"
test -f "$README"

echo "[2/9] integration contract exists"
test -f "$INTEGRATION"

echo "[3/9] README links integration contract"
grep -q "docs/INTEGRATION.md" "$README"

echo "[4/9] integration contract has bridge contract"
grep -q "Bridge contract" "$INTEGRATION"

echo "[5/9] integration contract has safety rules"
grep -q "Safety rules" "$INTEGRATION"

echo "[6/9] README contains fenced bash blocks"
grep -q '```bash' "$README"

echo "[7/9] README contains fenced text blocks"
grep -q '```text' "$README"

echo "[8/9] README code fences are balanced"
COUNT="$(grep -c '^```' "$README")"
if [ $((COUNT % 2)) -ne 0 ]; then
  echo "Unbalanced markdown fences: $COUNT" >&2
  exit 1
fi

echo "[9/9] repo cd helper is multiline"
grep -q 'mqhcd() {' "$README"
grep -q 'cd "$path" || return $?' "$README"

echo "OK: docs smoke test passed"
