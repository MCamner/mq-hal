#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE="${TMPDIR:-/tmp}"

echo "SMOKE: visual HAL"

python3 -m py_compile "$ROOT/scripts/visual_hal.py"

for cmd in analyze-diagram review-ui architecture-brief; do
  text_out="$TMP_BASE/mq-hal-${cmd}.txt"
  json_out="$TMP_BASE/mq-hal-${cmd}.json"

  "$ROOT/bin/mq-hal" "$cmd" --sample >"$text_out"
  grep -q "HAL" "$text_out"
  grep -q "Observations" "$text_out"
  grep -q "Trust boundaries" "$text_out"
  grep -q "YAML draft" "$text_out"
  grep -q "executable" "$text_out"

  "$ROOT/bin/mq-hal" "$cmd" --sample --json >"$json_out"
  python3 - "$json_out" "$cmd" <<'PY'
import json
import sys

path, expected = sys.argv[1], sys.argv[2]
data = json.load(open(path))
assert data["mode"] == expected
assert data["observations"]
assert data["trust_boundaries"]
assert data["yaml_draft"]
PY
done

missing_json="$TMP_BASE/mq-hal-visual-missing.json"
"$ROOT/bin/mq-hal" analyze-diagram "$TMP_BASE/does-not-exist.png" --json >"$missing_json"
python3 - "$missing_json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
assert data["mode"] == "analyze-diagram"
assert data["available"] is False
assert data["source"] == "deterministic-local"
assert data["yaml_draft"]["executable"] is False
PY

echo "OK: visual HAL smoke passed"
