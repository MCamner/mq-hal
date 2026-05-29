#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: router safety"

echo "[1/6] all ALLOWED_INTENTS have a handler in handle_intent"
python3 - "$ROOT" <<'EOF'
import sys, ast
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

source = open(root + "/scripts/hal.py").read()
tree = ast.parse(source)

handled = set()
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "handle_intent":
        for n in ast.walk(node):
            if (
                isinstance(n, ast.Compare)
                and isinstance(n.left, ast.Name)
                and n.left.id == "action"
            ):
                for comp in n.comparators:
                    if isinstance(comp, ast.Constant):
                        handled.add(comp.value)
        break

missing = hal.ALLOWED_INTENTS - handled
assert not missing, f"Intents with no handler: {missing}"
print(f"  {len(hal.ALLOWED_INTENTS)} intents, all handled: OK")
EOF

echo "[2/6] refuse intent exits 2"
python3 - "$ROOT" <<'EOF'
import sys
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

rc = hal.handle_intent({
    "schema": "mq-hal.intent.v1",
    "intent": "refuse",
    "repo": None,
    "command": None,
    "args": [],
    "message": "Jag kan inte göra det där säkert.",
})
assert rc == 2, f"Expected refuse to exit 2, got {rc}"
print("  refuse intent → exit 2: OK")
EOF

echo "[3/6] unknown mqlaunch command is rejected (exit 2)"
python3 - "$ROOT" <<'EOF'
import sys
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

rc = hal.handle_intent({
    "schema": "mq-hal.intent.v1",
    "intent": "run_mqlaunch",
    "repo": None,
    "command": "rm -rf /",
    "args": [],
    "message": "",
})
assert rc == 2, f"Expected exit 2 for unknown mqlaunch command, got {rc}"
print("  unknown mqlaunch command → exit 2: OK")
EOF

echo "[4/6] --confirm with 'n' cancels (exit 130)"
cancel_exit=0
echo "n" | "$ROOT/bin/mq-hal" --no-ai --confirm \
  "visa git status i mq-hal" >/dev/null 2>&1 || cancel_exit=$?
[ "$cancel_exit" -eq 130 ] || {
  echo "ERROR: expected exit 130 for confirm cancel, got $cancel_exit"
  exit 1
}
echo "  --confirm cancel → exit 130: OK"

echo "[5/6] empty prompt shows help (exit 0)"
"$ROOT/bin/mq-hal" >/dev/null
echo "  empty prompt → help, exit 0: OK"

echo "[6/6] ALLOWED_MQLAUNCH entries are valid command lists"
python3 - "$ROOT" <<'EOF'
import sys
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import hal

for key, cmd in hal.ALLOWED_MQLAUNCH.items():
    assert isinstance(cmd, list), \
        f"ALLOWED_MQLAUNCH[{key!r}] must be a list"
    assert cmd[0] == "mqlaunch", \
        f"ALLOWED_MQLAUNCH[{key!r}] must start with mqlaunch"
    assert len(cmd) >= 2, \
        f"ALLOWED_MQLAUNCH[{key!r}] must have at least 2 elements"
print(f"  {len(hal.ALLOWED_MQLAUNCH)} mqlaunch commands validated: OK")
EOF

echo "OK: router safety smoke test passed"
