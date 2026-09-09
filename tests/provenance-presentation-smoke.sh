#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: provenance-presentation"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

_fake() {
  # _fake <name> <record-file>
  cat >"$TMP/$1" <<SH
#!/usr/bin/env bash
set -euo pipefail
if [[ "\$*" != "stack provenance --json" ]]; then
  echo "unexpected mq-agent args: \$*" >&2
  exit 2
fi
cat "$2"
SH
  chmod +x "$TMP/$1"
}

# A record whose every displayed value is a sentinel, so the renderer cannot
# pass by producing something plausible of its own. It also carries a status
# and a reason code mq-hal has never heard of, and all four kinds of absence.
cat >"$TMP/rec_ok.json" <<'JSON'
{
  "schema": "mq.stack-provenance.v1",
  "generated_at": "2026-09-09T00:00:00Z",
  "components": [
    {
      "name": "comp-absent-install",
      "status": "PASS",
      "reasons": [],
      "checkout": {"head": "aaaaaaa1111111111111111111111111111111111"},
      "installed": null,
      "running": null,
      "running_probe": {"attempted": false, "endpoint": null, "reachable": null}
    },
    {
      "name": "comp-unknown-identity",
      "status": "WARN",
      "reasons": ["RTP999_FUTURE_REASON"],
      "checkout": {"head": "bbbbbbb2222222222222222222222222222222222"},
      "installed": {"commit": "ccccccc333", "identity_quality": "unknown"},
      "running": {"commit": "ddddddd444", "identity_quality": "verified"},
      "running_probe": {"attempted": true, "endpoint": "http://sentinel/probe", "reachable": false}
    },
    {
      "name": "comp-future-status",
      "status": "SOMETHING_NEW",
      "reasons": [],
      "checkout": {"head": "eeeeeee5555555555555555555555555555555555"},
      "installed": null,
      "running": null,
      "running_probe": {"attempted": true, "endpoint": null, "reachable": true}
    }
  ],
  "summary": {
    "status": "SOMETHING_NEW",
    "problem_count": 1,
    "next_action": "SENTINEL_ACTION_TEXT"
  }
}
JSON

for st in FAIL UNAVAILABLE; do
  python3 - "$TMP/rec_ok.json" "$TMP/rec_$st.json" "$st" <<'PY'
import json, sys
rec = json.load(open(sys.argv[1]))
rec["summary"]["status"] = sys.argv[3]
rec["components"][0]["status"] = sys.argv[3]
open(sys.argv[2], "w").write(json.dumps(rec, indent=2) + "\n")
PY
done

_fake ok "$TMP/rec_ok.json"
_fake fail "$TMP/rec_FAIL.json"
_fake unavailable "$TMP/rec_UNAVAILABLE.json"

cat >"$TMP/broken" <<'SH'
#!/usr/bin/env bash
echo "mq-agent exploded" >&2
exit 3
SH
chmod +x "$TMP/broken"

echo "[1/12] syntax"
python3 -m py_compile hal/provenance_view.py
python3 -m py_compile hal/provenance.py

echo "[2/12] every displayed value comes from the record"
MQ_AGENT_BIN="$TMP/ok" ./bin/mq-hal provenance > "$TMP/out.txt"
for needle in comp-absent-install comp-unknown-identity comp-future-status \
              aaaaaaa bbbbbbb eeeeeee ddddddd; do
  grep -q "$needle" "$TMP/out.txt" || { echo "missing sentinel: $needle" >&2; exit 1; }
done
# Each component's status must be the one the record supplies — not one the
# renderer worked out for itself. Without this, a renderer deriving status from
# the reason list would still pass every other assertion here, because only one
# component in the fixture carries reasons at all.
python3 - "$TMP/rec_ok.json" "$TMP/out.txt" <<'STATUSCHECK'
import json, sys
rec = json.load(open(sys.argv[1]))
lines = open(sys.argv[2]).read().splitlines()

def line_for(name):
    for line in lines:
        if line.startswith(name + " ") or line == name:
            return line
    raise SystemExit("no rendered line for " + name)

for comp in rec["components"]:
    line = line_for(comp["name"])
    shown = line[len(comp["name"]):].strip()
    if shown != comp["status"]:
        raise SystemExit(
            comp["name"] + ": record says " + repr(comp["status"])
            + ", renderer showed " + repr(shown)
        )

header = line_for("MQ Runtime Provenance")
shown = header[len("MQ Runtime Provenance"):].strip()
if shown != rec["summary"]["status"]:
    raise SystemExit(
        "summary: record says " + repr(rec["summary"]["status"])
        + ", showed " + repr(shown)
    )
STATUSCHECK
echo "   sentinels rendered, every status exactly as supplied"

echo "[3/12] an unfamiliar reason code is shown verbatim"
grep -q "RTP999_FUTURE_REASON" "$TMP/out.txt"
echo "   RTP999_FUTURE_REASON verbatim"

echo "[4/12] an unfamiliar status is shown verbatim"
grep -q "SOMETHING_NEW" "$TMP/out.txt"
echo "   SOMETHING_NEW verbatim"

echo "[5/12] next_action is shown exactly as supplied"
grep -q "SENTINEL_ACTION_TEXT" "$TMP/out.txt"
# The renderer must not have produced a remedy of its own alongside it.
for invented in restart reinstall rebuild "verify or update"; do
  if grep -qi "$invented" "$TMP/out.txt"; then
    echo "renderer produced its own remedy: $invented" >&2
    exit 1
  fi
done
echo "   SENTINEL_ACTION_TEXT exact, no invented remedy"

echo "[6/12] the four kinds of absence stay apart"
grep -q "not observed" "$TMP/out.txt"
grep -q "identity unknown" "$TMP/out.txt"
grep -q "not asked" "$TMP/out.txt"
grep -q "asked — unreachable" "$TMP/out.txt"
echo "   not observed / identity unknown / not asked / asked — unreachable"

echo "[7/12] colour keys on status only, unknown status stays neutral"
python3 -c "
import hal.provenance_view as P
P._colour_enabled = lambda: True
assert P._styled('PASS') == '\033[32mPASS\033[0m', repr(P._styled('PASS'))
assert P._styled('SOMETHING_NEW') == 'SOMETHING_NEW', repr(P._styled('SOMETHING_NEW'))
assert set(P.STATUS_STYLE) == {'PASS', 'WARN', 'FAIL', 'UNAVAILABLE'}, P.STATUS_STYLE
print('   known status styled, unknown status neutral and verbatim')
"

echo "[8/12] a record that was obtained always exits 0"
for f in ok fail unavailable; do
  MQ_AGENT_BIN="$TMP/$f" ./bin/mq-hal provenance >/dev/null
  MQ_AGENT_BIN="$TMP/$f" ./bin/mq-hal provenance --json >/dev/null
done
echo "   PASS / WARN / FAIL / UNAVAILABLE all exit 0"

echo "[9/12] transport failure exits non-zero and prints no provenance"
set +e
MQ_AGENT_BIN="$TMP/broken" ./bin/mq-hal provenance > "$TMP/broken_out.txt" 2> "$TMP/broken_err.txt"
rc=$?
MQ_AGENT_BIN="$TMP/broken" ./bin/mq-hal provenance --json > "$TMP/broken_json.txt" 2>/dev/null
rcj=$?
set -e
[ "$rc" -ne 0 ] || { echo "transport failure exited 0" >&2; exit 1; }
[ "$rcj" -ne 0 ] || { echo "transport failure exited 0 under --json" >&2; exit 1; }
[ ! -s "$TMP/broken_out.txt" ] || { echo "stdout carried output on failure" >&2; exit 1; }
[ ! -s "$TMP/broken_json.txt" ] || { echo "--json carried output on failure" >&2; exit 1; }
grep -q "exploded" "$TMP/broken_err.txt"
echo "   rc=$rc, stdout empty, stderr preserved"

echo "[10/12] --json is the producer's bytes, unchanged"
MQ_AGENT_BIN="$TMP/ok" ./bin/mq-hal provenance --json > "$TMP/json_out.txt"
cmp "$TMP/json_out.txt" "$TMP/rec_ok.json" \
  || { echo "--json differs from producer bytes" >&2; diff "$TMP/rec_ok.json" "$TMP/json_out.txt" >&2; exit 1; }
echo "   byte-identical to what the producer emitted"

echo "[11/12] presentation makes no reason-specific decision"
python3 -c "
import ast, re, sys

tree = ast.parse(open('hal/provenance_view.py').read())

docstrings = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        body = getattr(node, 'body', None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

# Presentation may read status, reasons and next_action — it has to. What it
# may not do is decide anything from a specific reason code, or word a remedy
# of its own. Both would need to appear here as code, not prose.
reason_code = re.compile(r'RTP[0-9]')
remedy = re.compile(r'\b(restart|reinstall|rebuild|reinstall)\b', re.I)

bad = []
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if id(node) in docstrings:
            continue
        if reason_code.search(node.value):
            bad.append(f'reason code in code: {node.value!r}')
        if remedy.search(node.value):
            bad.append(f'remedy wording in code: {node.value!r}')

# Presentation's only data source is the transport. It may not observe the
# world itself: no subprocess, no filesystem walk, no HTTP. Anything it learned
# on its own would be a provenance observation mq-agent never made.
observers = {'subprocess', 'shutil', 'urllib', 'http', 'socket', 'importlib', 'httpx', 'requests'}
imported = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported.update(a.name.split('.')[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported.add(node.module.split('.')[0])
leaked = imported & observers
if leaked:
    bad.append('presentation can observe: ' + ', '.join(sorted(leaked)))

if bad:
    print('presentation decides things it does not own:', file=sys.stderr)
    for b in bad:
        print('  ' + b, file=sys.stderr)
    raise SystemExit(1)
print('   no reason codes, no remedy wording, no way to observe')
"

echo "[12/12] the command is registered everywhere the repo requires"
grep -q "  provenance)" bin/mq-hal
grep -q "hal/provenance_view.py" bin/mq-hal
grep -q '`provenance`' docs/COMMAND_SURFACE.md
grep -q '### `provenance`' docs/hal-command-surface.md
python3 -c "
import json
names = {t['name'] for t in json.load(open('config/tools.json'))['tools']}
assert 'provenance' in names, 'provenance missing from config/tools.json'
"
./tools/check-command-docs.sh >/dev/null
echo "   bin route, both surface docs, tool registry"

echo "OK: provenance-presentation smoke passed"
