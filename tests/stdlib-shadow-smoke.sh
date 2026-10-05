#!/usr/bin/env bash
# No module that runs as a script may share a name with the standard library.
#
# bin/mq-hal runs hal/*.py and scripts/*.py directly, which puts that directory
# first on sys.path. hal/operator.py then shadowed the stdlib `operator`:
# argparse -> re -> functools -> collections -> `from operator import eq`
# loaded HAL's file, which imports json, which needs the half-loaded re. It
# only worked because Homebrew's Python imports collections at startup (via
# site) before sys.path[0] matters; a python.org build, or `python3 -S`,
# crashed on import.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPYCACHEPREFIX="$(mktemp -d)"

echo "SMOKE: no stdlib-shadowing script modules"

echo "[1/2] no hal/ or scripts/ module is named like a stdlib module"
python3 - "$ROOT" <<'EOF'
import subprocess, sys
from pathlib import Path
root = sys.argv[1]
files = subprocess.run(["git", "-C", root, "ls-files", "hal/*.py", "scripts/*.py"],
                       capture_output=True, text=True, check=True).stdout.split()
clashes = [f for f in files if Path(f).stem in sys.stdlib_module_names]
assert not clashes, f"shadows the standard library: {clashes}"
print(f"  {len(files)} modules checked")
EOF

echo "[2/2] every hal/ module runs without site (no preloaded stdlib)"
# -S skips site, so nothing is imported before the script's own directory
# is on sys.path: the condition a non-Homebrew interpreter starts in.
fails=0
for module in "$ROOT"/hal/*.py; do
  [[ "$(basename "$module")" == "__init__.py" ]] && continue
  if ! out="$(cd "$ROOT" && python3 -S -c "
import runpy, sys
sys.path.insert(0, 'hal')
sys.argv = ['x', '--help']
try:
    runpy.run_path('$module', run_name='not_main')
except SystemExit:
    pass
" 2>&1)"; then
    echo "  FAIL: $(basename "$module"): $(tail -1 <<<"$out")" >&2
    fails=$((fails + 1))
  fi
done
[[ "$fails" -eq 0 ]] || { echo "FAIL: $fails hal module(s) break without site" >&2; exit 1; }
echo "  all hal modules import cleanly"

echo "OK: stdlib shadow smoke test passed"
