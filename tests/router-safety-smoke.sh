#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: router safety"

echo "[1/7] all ALLOWED_INTENTS have a handler in handle_intent"
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

echo "[2/7] refuse intent exits 2"
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

echo "[3/7] unknown mqlaunch command is rejected (exit 2)"
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

echo "[4/7] --confirm cancels on 'n' (exit 130) — Python-level test"
python3 - "$ROOT" <<'EOF'
import sys, builtins
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/scripts")
import hal

# confirm_command returns False for 'n'
old_input = builtins.input
builtins.input = lambda _prompt: "n"
result = hal.confirm_command(["git", "--version"], Path("/tmp"))
builtins.input = old_input
assert not result, f"confirm_command should return False for 'n', got {result}"

# run_planned_command with confirm=True and 'n' → exit 130
old_input = builtins.input
builtins.input = lambda _prompt: "n"
rc = hal.run_planned_command(["git", "--version"], cwd=Path("/tmp"), confirm=True)
builtins.input = old_input
assert rc == 130, f"Expected exit 130 for confirm cancel, got {rc}"
print("  --confirm cancel → exit 130: OK")
EOF

echo "[5/7] empty prompt shows router help (exit 0)"
# The router, not a bare `bin/mq-hal`. A no-argument `mq-hal` is the dashboard
# (docs/COMMAND_SURFACE.md), which opens a prompt — so the old form of this
# step proved the dashboard reached EOF, not that the router prints help.
help_out="$(python3 "$ROOT/scripts/hal.py" </dev/null)"
echo "$help_out" | grep -q "usage: mq-hal"
echo "$help_out" | grep -q "Local HAL command router"
echo "  empty prompt → help, exit 0: OK"

echo "[6/7] ALLOWED_MQLAUNCH entries are valid command lists"
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

echo "[7/7] no release gate opens a prompt"
python3 - "$ROOT" <<'EOF'
import re
import sys
from pathlib import Path

# A release gate must terminate on its own. Two mq-hal surfaces read stdin
# until it answers or ends: a no-argument `mq-hal` (the dashboard) and
# `mq-hal dashboard` without --once/--json. Under a stdin that never delivers
# — a detached run whose pipe stays open — that read never returns, and the
# whole suite hangs rather than failing. A test may still drive the dashboard,
# but only through input it feeds itself.
INVOCATION = re.compile(r"(?:\$\{?ROOT\}?/|\./)?bin/mq-hal|\$\{?HAL\}?")
COMMAND_START = "|;&({}"
PREFIX_WORDS = {"if", "then", "else", "elif", "do", "exec", "env", "timeout", "!"}


def arguments(rest: str) -> list[str]:
    """Real arguments, with redirections and their targets removed."""
    args = []
    skip = False
    for token in rest.split():
        if skip:
            skip = False
            continue
        if re.fullmatch(r"[0-9]?[<>]{1,2}", token):
            skip = True  # the next token is the redirection target
            continue
        if re.match(r"^[0-9]?[<>&]", token):
            continue
        args.append(token)
    return args


def violations(text: str) -> list[str]:
    """Interactive invocations that inherit stdin instead of being fed."""
    found = []
    terminator = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        # Skip heredoc bodies: a test's embedded Python is not a shell command,
        # and scanning it would flag this step's own negative controls.
        if terminator is not None:
            if line == terminator:
                terminator = None
            continue
        opening = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if opening:
            terminator = opening.group(1)
            continue
        if not line or line.startswith("#"):
            continue
        flat = line.replace('"', "").replace("'", "")
        for match in INVOCATION.finditer(flat):
            before = flat[: match.start()].rstrip()
            word = before.split()[-1] if before.split() else ""
            starts_command = (
                not before or before[-1] in COMMAND_START or word in PREFIX_WORDS
            )
            if not starts_command:
                continue  # the path is an argument, not an invocation
            rest = flat[match.end() :]
            fed = "<" in rest or "|" in before
            args = arguments(rest)
            bare = not args
            dash = bool(args) and args[0] == "dashboard" and not (
                {"--once", "--json"} & set(args)
            )
            if (bare or dash) and not fed:
                found.append(f"line {number}: {line}")
    return found


root = Path(sys.argv[1])
offenders = {}
for path in sorted((root / "tests").glob("*.sh")):
    hits = violations(path.read_text())
    if hits:
        offenders[path.name] = hits

assert not offenders, "release gates that open a prompt: " + repr(offenders)

# Negative control: the rule is only worth anything if it can fire. This is
# the exact form this step was added to catch.
control = violations('"$ROOT/bin/mq-hal" >/dev/null')
assert control, "guard cannot detect a bare interactive invocation"
control = violations("./bin/mq-hal dashboard --sample --no-clear")
assert control, "guard cannot detect an unfed dashboard loop"
control = violations("printf 'q\\n' | ./bin/mq-hal dashboard --sample")
assert not control, "guard must allow a dashboard the test feeds itself"

print(f"  {len(list((root / 'tests').glob('*.sh')))} smoke tests, none opens a prompt: OK")
EOF

echo "OK: router safety smoke test passed"
