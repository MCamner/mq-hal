#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAKE="$TMP/mq-agent"
cat >"$FAKE" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
[[ "$1" == "feedback" ]] || exit 2
shift
case "$1" in
  status)
    printf '%s\n' '{"view":"feedback-status.v1","health":"HEALTHY","valid_records":3,"comparison_records":2,"candidate_events":1,"invalid_records":0,"newest_recorded_at":"2026-10-01T12:00:00Z","degraded_reasons":[]}'
    ;;
  report)
    printf '%s\n' '{"schema":"mq.feedback-report.v1","health":"HEALTHY","matched_records":3,"comparison":{"status":"available","records":2,"reason":"FUTURE_VERDICT_X"},"metrics":{"context_bytes":{"status":"measured","value":-1200}}}'
    ;;
  inspect)
    printf '%s\n' '{"view":"feedback-inspect.v1","feedback_run_id":"fb-1","comparison":{"record":{"verdict":"FUTURE_VERDICT_X","comparison_id":"cmp-1","evidence_refs":["experiments.jsonl:1"],"metrics":{"context_bytes":{"delta":-1200,"direction":"lower_is_better","material":true}}}},"candidate":{"record":{"candidate_id":"cand-1","state":"proposed"}}}'
    ;;
  compare)
    printf '%s\n' '{"schema":"mq.feedback-comparison.v1","verdict":"FUTURE_VERDICT_X","comparison_id":"cmp-1","evidence_refs":["experiments.jsonl:1"],"metrics":{"context_bytes":{"delta":-1200,"direction":"lower_is_better","material":true}}}'
    ;;
  candidates)
    printf '%s\n' '{"view":"feedback-candidates.v1","count":1,"candidates":[{"candidate_id":"cand-1","state":"proposed","task_class":"repo-review","proposed_strategy":"hybrid-context-v1"}]}'
    ;;
  *)
    exit 2
    ;;
esac
SH
chmod +x "$FAKE"
export MQ_AGENT_BIN="$FAKE"
export PYTHONPYCACHEPREFIX="$TMP/pycache"

echo "SMOKE: feedback control"

echo "[1/7] status JSON preserves producer contract"
out="$("$ROOT/bin/mq-hal" feedback status --json)"
python3 - "$out" <<'PY'
import json, sys
d=json.loads(sys.argv[1])
assert d["view"]=="feedback-status.v1"
assert d["health"]=="HEALTHY"
assert d["comparison_records"]==2
PY

echo "[2/7] default command is status"
"$ROOT/bin/mq-hal" feedback | grep -q "MQ Feedback Engine"

echo "[3/7] future verdict is rendered verbatim"
out="$("$ROOT/bin/mq-hal" feedback report)"
echo "$out" | grep -q "FUTURE_VERDICT_X"
! echo "$out" | grep -q "Verdict:     PASS"
! echo "$out" | grep -q "Verdict:     WARN"
! echo "$out" | grep -q "Verdict:     FAIL"

echo "[4/7] inspect exposes producer candidate and navigation only"
out="$("$ROOT/bin/mq-hal" feedback inspect fb-1)"
echo "$out" | grep -q "Candidate: cand-1"
echo "$out" | grep -q "mq-agent feedback candidate cand-1"

echo "[5/7] comparison deltas are shown without recomputation"
out="$("$ROOT/bin/mq-hal" feedback compare fb-1)"
echo "$out" | grep -q "context_bytes: delta=-1200"
echo "$out" | grep -q "direction=lower_is_better"

echo "[6/7] candidate list is read-only navigation"
out="$("$ROOT/bin/mq-hal" feedback candidates)"
echo "$out" | grep -q "cand-1"
echo "$out" | grep -q "review: mq-agent feedback candidate cand-1"

echo "[7/7] mutating feedback commands are not exposed"
set +e
"$ROOT/bin/mq-hal" feedback run >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" -ne 0 ]]

echo "OK: feedback control smoke test passed"
