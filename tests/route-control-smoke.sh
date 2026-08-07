#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TMPBIN="$(mktemp -d)"
trap 'rm -rf "$TMPBIN"' EXIT

cat >"$TMPBIN/mq-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "route inspect "*" --agent codex --json")
    cat <<'JSON'
{"schema":"mq.model-route-decision.v1","decision_id":"route-test","task_class":"docs-review","risk":"low","recommended_route":"local-shadow","local_model":"qwen3:4b-instruct","authoritative_agent":"codex","reason_codes":["read-only"],"escalation_conditions":["verification-failed"]}
JSON
    ;;
  "route report --json")
    cat <<'JSON'
{"schema":"mq.model-route-report.v1","source":"fixture","total_records":10,"valid_outcomes":10,"invalid_records":0,"attempted":8,"model_output_received":8,"schema_valid":7,"verified":5,"accepted_by_agent":4,"accepted_by_operator":3,"escalated":2,"by_task_class":{"docs-review":{"total":6,"verified":5,"accepted_by_agent":4,"escalated":1}}}
JSON
    ;;
  "route history --limit 20 --json")
    cat <<'JSON'
{"schema":"mq.model-route-history.v1","source":"fixture","total_records":2,"valid_outcomes":2,"invalid_records":0,"filters":{"decision_id":null,"task_class":null},"matched":2,"returned":2,"entries":[{"schema":"mq.model-route-outcome.v1","decision_id":"route-test","run_id":"run-b","task_class":"docs-review","selected_route":"local-shadow","local_model":"qwen3:4b-instruct","authoritative_agent":"codex","attempted":true,"model_output_received":true,"schema_valid":false,"verification":{"status":"FAIL","checks":["candidate-schema"]},"accepted_by_agent":false,"accepted_by_operator":false,"escalated":true,"escalation_reason":"verification-failed","recorded_at":"2026-08-07T12:00:00Z"},{"schema":"mq.model-route-outcome.v1","decision_id":"route-test","run_id":"run-a","task_class":"docs-review","selected_route":"local-shadow","local_model":"qwen3:4b-instruct","authoritative_agent":"codex","attempted":true,"model_output_received":true,"schema_valid":true,"verification":{"status":"PASS","checks":["candidate-schema","task-class-match"]},"accepted_by_agent":true,"accepted_by_operator":false,"escalated":false,"escalation_reason":null,"recorded_at":"2026-08-07T10:00:00Z"}]}
JSON
    ;;
  "route history --limit 20 --decision-id route-test --json")
    cat <<'JSON'
{"schema":"mq.model-route-history.v1","source":"fixture","total_records":2,"valid_outcomes":2,"invalid_records":0,"filters":{"decision_id":"route-test","task_class":null},"matched":1,"returned":1,"entries":[{"schema":"mq.model-route-outcome.v1","decision_id":"route-test","run_id":"run-b","task_class":"docs-review","selected_route":"local-shadow","local_model":"qwen3:4b-instruct","authoritative_agent":"codex","attempted":true,"model_output_received":true,"schema_valid":false,"verification":{"status":"FAIL","checks":["candidate-schema"]},"accepted_by_agent":false,"accepted_by_operator":false,"escalated":true,"escalation_reason":"verification-failed","recorded_at":"2026-08-07T12:00:00Z"}]}
JSON
    ;;
  "route history --limit 20 --decision-id route-missing --json")
    cat <<'JSON'
{"schema":"mq.model-route-history.v1","source":"fixture","total_records":2,"valid_outcomes":2,"invalid_records":0,"filters":{"decision_id":"route-missing","task_class":null},"matched":0,"returned":0,"entries":[]}
JSON
    ;;
  "models doctor --no-smoke --json")
    cat <<'JSON'
{"schema":"ollama_runtime_doctor.v1","ok":true,"installed_models":["qwen3:4b-instruct"],"items":[{"check":"ollama-version","status":"PASS","detail":"available"}]}
JSON
    ;;
  *)
    echo "unexpected mq-agent args: $*" >&2
    exit 2
    ;;
esac
SH
chmod +x "$TMPBIN/mq-agent"
export MQ_AGENT_BIN="$TMPBIN/mq-agent"

echo "SMOKE: model routing control room"

python3 -m py_compile hal/route.py

./bin/mq-hal route --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["schema"] == "mq_hal.model_route.v1"
assert d["status"] == "PASS"
assert d["mode"] == "SHADOW"
assert d["authoritative_agent"] == "codex"
assert d["metrics"]["verified"] == 5
assert d["feedback"]["schema"] == "mq.feedback.v1"
'

./bin/mq-hal route status | grep -q "MQ Model Routing"
./bin/mq-hal route status | grep -q "Authoritative agent: codex"
./bin/mq-hal route inspect "Review docs" | grep -q "Decision: route-test"

./bin/mq-hal route accuracy --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["verified_outcomes"] == 5
assert d["by_task_class"]["docs-review"]["verified"] == 5
assert d["by_task_class"]["docs-review"]["acceptance_rate"] == 0.8
'

./bin/mq-hal route history --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["schema"] == "mq_hal.model_route_history.v1"
assert d["status"] == "PASS", d
assert d["matched"] == 2 and d["returned"] == 2
newest, oldest = d["history"]
assert newest["run_id"] == "run-b"
assert newest["verification"]["status"] == "FAIL"
assert newest["escalation_reason"] == "verification-failed"
assert oldest["model_output_received"] is True
assert oldest["accepted_by_agent"] is True
'

./bin/mq-hal route history | grep -q "run-b"
./bin/mq-hal route history | grep -q "verification-failed"

./bin/mq-hal route explain route-test --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["schema"] == "mq_hal.model_route_explain.v1"
assert d["status"] == "PASS", d
assert d["decision_id"] == "route-test"
assert [entry["run_id"] for entry in d["history"]] == ["run-b"]
'

./bin/mq-hal route explain route-missing --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "WARN"
assert d["decision_id"] == "route-missing"
assert d["history"] == []
assert d["reason"] == "routing-decision-not-found"
'

if ./bin/mq-hal route nope >/dev/null 2>&1; then
  echo "unknown route subcommand unexpectedly accepted" >&2
  exit 1
fi

cat >"$TMPBIN/mq-agent-no-history" <<'SH'
#!/usr/bin/env bash
echo "No such command 'history'." >&2
exit 2
SH
chmod +x "$TMPBIN/mq-agent-no-history"
MQ_AGENT_BIN="$TMPBIN/mq-agent-no-history" ./bin/mq-hal route history --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "WARN"
assert d["history"] == []
assert d["reason"] == "verified-routing-history-unavailable"
'

MQ_AGENT_BIN="$TMPBIN/missing" ./bin/mq-hal route --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "WARN"
assert d["router"] == "UNAVAILABLE"
'

echo "OK: model routing control room smoke passed"
