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
assert d["status"] == "WARN"
assert d["history"] == []
'

./bin/mq-hal route explain route-missing --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "WARN"
assert d["decision_id"] == "route-missing"
'

if ./bin/mq-hal route nope >/dev/null 2>&1; then
  echo "unknown route subcommand unexpectedly accepted" >&2
  exit 1
fi

MQ_AGENT_BIN="$TMPBIN/missing" ./bin/mq-hal route --json | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "WARN"
assert d["router"] == "UNAVAILABLE"
'

echo "OK: model routing control room smoke passed"
