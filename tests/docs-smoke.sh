#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="$ROOT/README.md"
INTEGRATION="$ROOT/docs/INTEGRATION.md"
SURFACE="$ROOT/docs/hal-command-surface.md"

echo "SMOKE: docs"

echo "[1/18] README exists"
test -f "$README"

echo "[2/18] integration contract exists"
test -f "$INTEGRATION"

echo "[3/18] command surface reference exists"
test -f "$SURFACE"

echo "[4/18] README links integration contract"
grep -q "docs/INTEGRATION.md" "$README"

echo "[5/18] README links command surface"
grep -q "docs/hal-command-surface.md" "$README"

echo "[6/18] integration contract has bridge contract"
grep -q "Bridge contract" "$INTEGRATION"

echo "[7/18] integration contract has safety rules"
grep -q "Safety rules" "$INTEGRATION"

echo "[8/18] README contains fenced bash blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "bash"
raise SystemExit(0 if needle in s else 1)
PY

echo "[9/18] README contains fenced text blocks"
python3 - "$README" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
needle = chr(96) * 3 + "text"
raise SystemExit(0 if needle in s else 1)
PY

echo "[10/18] README code fences are balanced"
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

echo "[11/18] README code fences have clean info strings"
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

echo "[12/18] README documents current HAL command groups"
grep -q "mq-hal release-brief" "$README"
grep -q "mq-hal audit" "$README"
grep -q "mq-hal stack-status" "$README"
grep -q "mq-hal repo-status" "$README"
grep -q "mq-hal ci" "$README"
grep -q "mq-hal context" "$README"
grep -q "mq-hal runtime" "$README"
grep -q "mq-hal config-check" "$README"

echo "[13/18] README documents operator front door sections"
grep -q "## Operator Role" "$README"
grep -q "## Safety Boundary" "$README"
grep -q "## Operator Views" "$README"

echo "[14/18] README points detailed command truth to docs"
grep -q "docs/COMMAND_SURFACE.md" "$README"
grep -q "docs/hal-command-surface.md" "$README"

echo "[15/18] command surface references audit and release-brief"
grep -q "audit" "$SURFACE"
grep -q "stack-status" "$SURFACE"
grep -q "release-brief" "$SURFACE"

echo "[16/18] docs/COMMAND_SURFACE.md exists"
test -f "$ROOT/docs/COMMAND_SURFACE.md"

echo "[17/18] install doc exists and is linked"
test -f "$ROOT/docs/INSTALL.md"
grep -q "docs/INSTALL.md" "$README"

echo "[18/18] terminal demo doc exists and is linked"
test -f "$ROOT/docs/TERMINAL_DEMO.md"
grep -q "docs/TERMINAL_DEMO.md" "$README"

echo "[guard] README markdown guard"
python3 "$ROOT/tools/markdown_guard.py" "$README"

echo "[version-sync] docs/index.html matches VERSION"
VERSION="$(cat "$ROOT/VERSION")"
PAGES="$ROOT/docs/index.html"
if [[ -f "$PAGES" ]]; then
  grep -q "v${VERSION}" "$PAGES" || {
    echo "FAIL: docs/index.html does not reference v${VERSION}" >&2
    exit 1
  }
fi

echo "OK: docs smoke test passed"
