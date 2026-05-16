#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "SMOKE: docs"

echo "[1/6] README exists"
test -f "$ROOT/README.md"

echo "[2/6] integration contract exists"
test -f "$ROOT/docs/INTEGRATION.md"

echo "[3/6] README links integration contract"
grep -q "docs/INTEGRATION.md" "$ROOT/README.md"

echo "[4/6] integration contract has bridge contract"
grep -q "Bridge contract" "$ROOT/docs/INTEGRATION.md"

echo "[5/6] integration contract has safety rules"
grep -q "Safety rules" "$ROOT/docs/INTEGRATION.md"

echo "[6/6] README contains fenced bash blocks"
grep -q '```bash' "$ROOT/README.md"

echo "OK: docs smoke test passed"
