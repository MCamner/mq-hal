#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="$ROOT/README.md"
INTEGRATION="$ROOT/docs/INTEGRATION.md"

echo "SMOKE: docs"

echo "[1/10] README exists"
test -f "$README"

echo "[2/10] integration contract exists"
test -f "$INTEGRATION"

echo "[3/10] README links integration contract"
grep -q "docs/INTEGRATION.md" "$README"

echo "[4/10] integration contract has bridge contract"
grep -q "Bridge contract" "$INTEGRATION"

echo "[5/10] integration contract has safety rules"
grep -q "Safety rules" "$INTEGRATION"

echo "[6/10] README contains fenced bash blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "bash"
raise SystemExit(0 if needle in s else 1)
PY

echo "[7/10] README contains fenced text blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "text"
raise SystemExit(0 if needle in s else 1)
PY

echo "[8/10] README code fences are balanced"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text().splitlines()
count = sum(1 for line in s if line.startswith(chr(96) * 3))
if count % 2 != 0:
    print(f"Unbalanced markdown fences: {count}", file=sys.stderr)
    raise SystemExit(1)
print(f"Balanced markdown fences: {count}")
PY

echo "[9/10] README documents Repo Ops"
grep -q "HAL Repo Ops" "$README"
grep -q "mq-hal repo-status" "$README"
grep -q "mq-hal ci" "$README"

echo "[10/10] repo cd helper is multiline"
grep -q 'mqhcd()' "$README"
grep -q 'cd "$path" || return $?' "$README"

echo "OK: docs smoke test passed"
