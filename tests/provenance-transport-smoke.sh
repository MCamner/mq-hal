#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: provenance-transport"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# A provenance record carrying a reason code mq-hal has never heard of and a
# sentinel next_action. Transport must not care about either.
RECORD='{"schema":"mq.stack-provenance.v1","generated_at":"2026-09-08T00:00:00Z","components":[{"name":"mq-agent","status":"WARN","reasons":["RTP999_FUTURE_REASON"]}],"summary":{"next_action":"SENTINEL"}}'

_fake() {
  # _fake <name> <body>
  cat >"$TMP/$1" <<SH
#!/usr/bin/env bash
set -euo pipefail
if [[ "\$*" != "stack provenance --json" ]]; then
  echo "unexpected mq-agent args: \$*" >&2
  exit 2
fi
$2
SH
  chmod +x "$TMP/$1"
}

_fake ok "printf '%s\n' '$RECORD'"
_fake slow "sleep 5"
_fake nonzero "echo 'mq-agent exploded' >&2; exit 3"
_fake badjson "printf '%s\n' 'not json{'"
_fake array "printf '%s\n' '[1,2,3]'"
_fake string "printf '%s\n' '\"just a string\"'"
_fake wrongschema "printf '%s\n' '{\"schema\":\"mq.execution-outcome.v1\",\"components\":[]}'"

# Exists but is not executable — subprocess raises OSError (PermissionError).
printf '%s\n' '#!/usr/bin/env bash' >"$TMP/noexec"
chmod 000 "$TMP/noexec"

echo "[1/10] syntax"
python3 -m py_compile hal/provenance.py
python3 -m py_compile hal/stack.py

echo "[2/10] mq-agent missing — unavailable, rc 127"
env -u MQ_AGENT_BIN HOME="$TMP/emptyhome" PATH="/usr/bin:/bin" \
  python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert r.returncode == 127, r.returncode
assert r.ok is False
assert 'not found' in r.error, r.error
print('   rc=127', r.error)
"

echo "[3/10] timeout — unavailable, rc 124"
MQ_AGENT_BIN="$TMP/slow" python3 -c "
from hal.provenance import read_provenance
r = read_provenance(timeout=1)
assert r.data is None, r
assert r.returncode == 124, r.returncode
print('   rc=124', r.error)
"

echo "[4/10] OSError — unavailable"
MQ_AGENT_BIN="$TMP/noexec" python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert r.ok is False
assert r.error, 'OSError message must be preserved'
print('   ', r.error)
"

echo "[5/10] non-zero exit — unavailable, stderr preserved"
MQ_AGENT_BIN="$TMP/nonzero" python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert r.returncode == 3, r.returncode
assert 'exploded' in r.error, r.error
print('   rc=3', r.error)
"

echo "[6/10] unparseable output — unavailable, raw preserved"
MQ_AGENT_BIN="$TMP/badjson" python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert 'not json{' in r.raw, r.raw
assert 'parse' in r.error, r.error
print('   ', r.error)
"

echo "[7/10] wrong top-level shape — array and string both rejected"
for f in array string; do
  MQ_AGENT_BIN="$TMP/$f" python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert 'not an object' in r.error, r.error
"
done
echo "   array and string rejected"

echo "[8/10] object with the wrong contract identity — rejected"
MQ_AGENT_BIN="$TMP/wrongschema" python3 -c "
from hal.provenance import read_provenance
r = read_provenance()
assert r.data is None, r
assert 'mq.stack-provenance.v1' in r.error, r.error
assert 'execution-outcome' in r.error, r.error
print('   ', r.error)
"

echo "[9/10] a provenance record is handed through unchanged"
MQ_AGENT_BIN="$TMP/ok" RECORD="$RECORD" python3 -c "
import json, os
from hal.provenance import read_provenance
r = read_provenance()
expected = json.loads(os.environ['RECORD'])
assert r.ok is True, r
assert r.returncode == 0 and r.error == ''
# Identical: nothing added, removed, renamed, or normalized.
assert r.data == expected, f'record was altered in transit:\n{r.data}\n{expected}'
# The consumer must not interpret an unknown reason code, only carry it.
assert r.data['components'][0]['reasons'] == ['RTP999_FUTURE_REASON']
assert r.data['summary']['next_action'] == 'SENTINEL'
print('   RTP999 and SENTINEL survived transport verbatim')
"

echo "[10/10] transport never speaks provenance vocabulary"
python3 -c "
import ast, sys

tree = ast.parse(open('hal/provenance.py').read())

# Docstrings are allowed to discuss provenance; code is not allowed to
# produce it. Collect the docstring nodes so they can be excluded.
docstrings = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        body = getattr(node, 'body', None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

# A consumer that synthesizes a finding would have to name one of these.
forbidden = {
    'status', 'reasons', 'reason', 'next_action', 'summary',
    'PASS', 'WARN', 'FAIL', 'UNAVAILABLE', 'UNKNOWN',
}
found = []
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id in forbidden:
        found.append(node.id)
    elif isinstance(node, ast.Attribute) and node.attr in forbidden:
        found.append(node.attr)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        if id(node) not in docstrings and node.value in forbidden:
            found.append(repr(node.value))

if found:
    print('transport names provenance vocabulary: ' + ', '.join(sorted(set(found))), file=sys.stderr)
    raise SystemExit(1)
print('   no status, reasons, next_action or verdict vocabulary in code')
"

echo "OK: provenance-transport smoke passed"
