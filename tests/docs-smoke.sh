#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="$ROOT/README.md"
INTEGRATION="$ROOT/docs/INTEGRATION.md"
SURFACE="$ROOT/docs/hal-command-surface.md"

echo "SMOKE: docs"

echo "[1/15] README exists"
test -f "$README"

echo "[2/15] integration contract exists"
test -f "$INTEGRATION"

echo "[3/15] command surface reference exists"
test -f "$SURFACE"

echo "[4/15] README links integration contract"
grep -q "docs/INTEGRATION.md" "$README"

echo "[5/15] README links command surface"
grep -q "docs/hal-command-surface.md" "$README"

echo "[6/15] integration contract has bridge contract"
grep -q "Bridge contract" "$INTEGRATION"

echo "[7/15] integration contract has safety rules"
grep -q "Safety rules" "$INTEGRATION"

echo "[8/15] README contains fenced bash blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "bash"
raise SystemExit(0 if needle in s else 1)
PY

echo "[9/15] README contains fenced text blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "text"
raise SystemExit(0 if needle in s else 1)
PY

echo "[10/15] README code fences are balanced"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
lines = Path(sys.argv[1]).read_text().splitlines()
count = sum(1 for line in lines if line.startswith(chr(96) * 3))
if count % 2 != 0:
    print(f"Unbalanced markdown fences: {count}", file=sys.stderr)
    raise SystemExit(1)
print(f"Balanced markdown fences: {count}")
PY

echo "[11/15] README code fences have clean info strings"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
bad = []
for i, line in enumerate(Path(sys.argv[1]).read_text().splitlines(), start=1):
    if line.startswith(chr(96) * 3) and " id=" in line:
        bad.append((i, line))
if bad:
    for line_no, line in bad:
        print(f"Bad fence at {line_no}: {line}", file=sys.stderr)
    raise SystemExit(1)
PY

echo "[12/15] README documents current HAL commands"
grep -q "mq-hal release-brief" "$README"
grep -q "mq-hal audit" "$README"
grep -q "mq-hal repo-status" "$README"
grep -q "mq-hal ci" "$README"
grep -q "mq-hal fix-doctor" "$README"

echo "[13/15] README documents Repo Ops"
grep -q "HAL Repo Ops" "$README"

echo "[14/15] repo cd helper is multiline"
grep -q 'mqhcd()' "$README"
grep -q 'cd "$path" || return $?' "$README"

echo "[15/15] command surface references audit and release-brief"
grep -q "audit" "$SURFACE"
grep -q "release-brief" "$SURFACE"

echo "[guard] README markdown guard"
python3 "$ROOT/tools/markdown_guard.py" "$README"

echo "OK: docs smoke test passed"
