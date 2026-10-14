#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

echo "SMOKE: compatibility"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Sentinel report: a future status, a future code, a pairwise finding, a
# future field at top level. Nothing here is vocabulary mq-hal may translate.
cat >"$TMP/fail.json" <<'JSON'
{"schema":"mq.stack-compatibility.v1","status":"FAIL","mode":"static","components":[{"repo":"comp-sentinel","status":"SOMETHING_NEW"}],"relationships":[{"producer":"prod-sentinel","consumer":"cons-sentinel","subject":"subject-sentinel","status":"FAIL","overlap":null,"detail":"detail-sentinel"}],"findings":[{"code":"MQC999_FUTURE_CODE","severity":"FAIL","repo":"cons-sentinel","repos":["cons-sentinel","prod-sentinel"],"message":"message-sentinel","blocks_release":true}],"next_action":"ACTION-SENTINEL","checked_at":"2026-10-14T00:00:00Z","future_extension":{"opaque":true}}
JSON
sed 's/"status":"FAIL","mode"/"status":"PASS","mode"/' "$TMP/fail.json" >"$TMP/pass.json"

_fake() {
  # _fake <name> <body>
  cat >"$TMP/$1" <<SH
#!/usr/bin/env bash
set -euo pipefail
if [[ "\$*" != "stack compatibility --json" ]]; then
  echo "unexpected mq-agent args: \$*" >&2
  exit 9
fi
$2
SH
  chmod +x "$TMP/$1"
}

_fake pass "cat '$TMP/pass.json'"
_fake fail "cat '$TMP/fail.json'; exit 2"
_fake unavailable "cat '$TMP/pass.json' | sed 's/\"PASS\"/\"UNAVAILABLE\"/'; exit 3"
_fake interrupted "cat '$TMP/pass.json'; exit 130"
_fake slow "sleep 5"
_fake badjson "printf '%s\n' 'not json{'"
_fake wrongschema "printf '%s\n' '{\"schema\":\"mq.stack-provenance.v1\"}'"

echo "[1/11] syntax"
python3 -m py_compile hal/compatibility.py hal/compatibility_view.py

echo "[2/11] mq-agent missing — no report, rc 127"
env -u MQ_AGENT_BIN HOME="$TMP/emptyhome" PATH="/usr/bin:/bin" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.data is None and r.returncode == 127 and not r.ok, r
"

echo "[3/11] timeout — no report, rc 124"
MQ_AGENT_BIN="$TMP/slow" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility(timeout=1)
assert r.data is None and r.returncode == 124, r
"

echo "[4/11] PASS report carried unchanged, unknown fields kept"
MQ_AGENT_BIN="$TMP/pass" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.ok and r.returncode == 0, r
assert r.data['future_extension'] == {'opaque': True}, r.data
"

echo "[5/11] FAIL exit 2 is still a report"
MQ_AGENT_BIN="$TMP/fail" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.ok and r.returncode == 2 and r.data['status'] == 'FAIL', r
"

echo "[6/11] UNAVAILABLE exit 3 is still a report"
MQ_AGENT_BIN="$TMP/unavailable" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.ok and r.returncode == 3 and r.data['status'] == 'UNAVAILABLE', r
"

echo "[7/11] interrupted (130) is not a report, even with stdout"
MQ_AGENT_BIN="$TMP/interrupted" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.data is None and r.returncode == 130, r
"

echo "[8/11] unparseable and wrong-schema output are not reports"
for f in badjson wrongschema; do
  MQ_AGENT_BIN="$TMP/$f" python3 -c "
from hal.compatibility import read_compatibility
r = read_compatibility()
assert r.data is None and r.returncode != 0, r
"
done

echo "[9/11] human view shows sentinels verbatim and passes the exit code through"
set +e
out="$(MQ_AGENT_BIN="$TMP/fail" NO_COLOR=1 python3 hal/compatibility_view.py)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "expected exit 2, got $rc" >&2; exit 1; }
for s in comp-sentinel SOMETHING_NEW "prod-sentinel → cons-sentinel" subject-sentinel detail-sentinel \
         MQC999_FUTURE_CODE message-sentinel ACTION-SENTINEL; do
  grep -qF -- "$s" <<<"$out" || { echo "missing in view: $s" >&2; echo "$out" >&2; exit 1; }
done

echo "[10/11] --json prints the producer's bytes exactly"
set +e
json_out="$(MQ_AGENT_BIN="$TMP/fail" python3 hal/compatibility_view.py --json)"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "expected exit 2, got $rc" >&2; exit 1; }
[[ "$json_out" == "$(cat "$TMP/fail.json")" ]] || { echo "--json re-serialized the report" >&2; exit 1; }

echo "[11/11] no report: stderr only, empty stdout; transport names no finding vocabulary"
set +e
missing_out="$(env -u MQ_AGENT_BIN HOME="$TMP/emptyhome" PATH="/usr/bin:/bin" python3 hal/compatibility_view.py --json 2>/dev/null)"
rc=$?
set -e
[[ "$rc" -eq 127 && -z "$missing_out" ]] || { echo "expected rc 127 and empty stdout, got $rc" >&2; exit 1; }
if grep -nE 'MQC[0-9]|blocks_release|next_action|"FAIL"|"PASS"' hal/compatibility.py; then
  echo "transport names compatibility vocabulary" >&2
  exit 1
fi

echo "PASS: compatibility smoke"
