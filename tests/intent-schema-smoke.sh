#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: intent schema contract"

echo "[1/7] schemas/intent.schema.json exists"
test -f "$ROOT/schemas/intent.schema.json"

echo "[2/7] schemas/intent.schema.json is valid JSON"
python3 -c "import json; json.load(open('$ROOT/schemas/intent.schema.json'))"

echo "[3/7] schema enum matches hal.py ALLOWED_INTENTS"
python3 - "$ROOT" <<'EOF'
import sys, json
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

schema = json.load(open(root + "/schemas/intent.schema.json"))
schema_enum = set(schema["properties"]["intent"]["enum"])
allowed = hal.ALLOWED_INTENTS

missing = allowed - schema_enum
extra = schema_enum - allowed

assert not missing, f"In ALLOWED_INTENTS but missing from schema enum: {missing}"
assert not extra, f"In schema enum but not in ALLOWED_INTENTS: {extra}"
print("  enum parity: OK")
EOF

echo "[4/7] unknown intent is normalized to refuse"
python3 - "$ROOT" <<'EOF'
import sys, json
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

result = hal.parse_intent(json.dumps({
    "schema": "mq-hal.intent.v1",
    "intent": "rm_rf",
    "repo": None,
    "command": None,
    "args": [],
    "message": ""
}))
assert result["intent"] == "refuse", f"Expected refuse, got: {result['intent']}"
print("  unknown intent → refuse: OK")
EOF

echo "[5/7] malformed JSON is normalized to refuse"
python3 - "$ROOT" <<'EOF'
import sys
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

result = hal.parse_intent("this is not json { broken")
assert result["intent"] == "refuse", f"Expected refuse for malformed JSON, got: {result['intent']}"
print("  malformed JSON → refuse: OK")
EOF

echo "[6/7] path escape outside repo is rejected"
python3 - "$ROOT" <<'EOF'
import sys, pathlib
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

base = pathlib.Path("/tmp/safe-repo")
result = hal.resolve_repo_path_arg(base, "../../etc/passwd")
assert result is None, f"Expected None for path escape, got: {result}"
print("  path escape → None: OK")
EOF

echo "[7/7] invalid branch names are rejected"
python3 - "$ROOT" <<'EOF'
import sys
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

bad = ["-starts-with-dash", "/starts/with/slash", ".lock", "has space", "", "a" * 121]
for name in bad:
    assert not hal.valid_branch_name(name), f"Expected invalid branch name to fail: {repr(name)}"

good = ["feature/hal-router", "fix-123", "release/0.11.0"]
for name in good:
    assert hal.valid_branch_name(name), f"Expected valid branch name to pass: {repr(name)}"

print("  branch name validation: OK")
EOF

echo "OK: intent schema smoke test passed"
