#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: mq-hal code-plan"

echo "[1/11] syntax check"
python3 -m py_compile "$ROOT/scripts/code_plan.py"
bash -n "$ROOT/bin/mq-hal"

echo "[2/11] the two surfaces are different commands, not one command with a flag"
python3 - "$ROOT" <<'PY'
import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
dispatcher = (root / "bin" / "mq-hal").read_text()

# Rule 2: cloud execution belongs to a command surface. `plan` must reach the
# local planner and nothing else; `code-plan` must reach the cloud script and
# nothing else. A shared arm would put the trust boundary back in a flag.
arms = dict(re.findall(r"^  ([a-z-]+)\)\n\s+shift \|\| true\n\s+exec python3 \"\$ROOT/([^\"]+)\"", dispatcher, re.M))
assert arms.get("plan") == "scripts/planner.py", arms.get("plan")
assert arms.get("code-plan") == "scripts/code_plan.py", arms.get("code-plan")

# And the cloud script is the only place the transport is imported, so grep for
# the import is a complete answer to "what can reach the network".
importers = []
for path in sorted((root / "scripts").glob("*.py")) + sorted((root / "hal").glob("*.py")):
    if path.name == "provider.py":
        continue
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        names = set()
        if isinstance(node, ast.Import):
            names = {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names = {node.module or ""} | {a.name for a in node.names}
        if any("provider" in n for n in names):
            importers.append(path.name)
            break

assert importers == ["code_plan.py"], f"provider transport reached from: {importers}"
print("  plan → planner.py, code-plan → code_plan.py, one importer of the transport: OK")
PY

echo "[3/11] a request that does not name a provider is not made"
python3 - "$ROOT" <<'PY'
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan

calls = []

def attempt(argv):
    out, err = io.StringIO(), io.StringIO()
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("urllib.request.urlopen", lambda *a, **k: calls.append(1)):
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    code = code_plan.main(argv)
                except SystemExit as exc:  # argparse
                    code = exc.code
    return code, out.getvalue(), err.getvalue()

# There is no default provider, so each of these is an invocation error rather
# than a request made on the operator's behalf.
REFUSED = [
    ["--repo", "mq-hal", "fix the release gate"],          # no --provider
    ["--provider", "openai", "fix the release gate"],      # no --repo
    ["--provider", "openai", "--repo", "mq-hal"],          # no goal
    ["--provider", "anthropic", "--repo", "mq-hal", "x"],  # not a known provider
    ["--provider", "", "--repo", "mq-hal", "x"],
    ["--provider", "openai", "--repo", "   ", "x"],
]
for argv in REFUSED:
    code, out, err = attempt(argv)
    assert code == code_plan.EXIT_INVOCATION, f"{argv} → {code}"
    assert "cloud egress:" not in err, err

assert calls == [], f"an invocation error must not reach the network: {calls}"
print(f"  {len(REFUSED)} incomplete invocations refused, 0 network calls: OK")
PY

echo "[4/11] a missing credential is exit 3, before any transfer"
python3 - "$ROOT" <<'PY'
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan

calls = []
out, err = io.StringIO(), io.StringIO()
with patch.dict("os.environ", {}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: calls.append(1)):
        with redirect_stdout(out), redirect_stderr(err):
            code = code_plan.main(["--provider", "openai", "--repo", "mq-hal", "släpp v2.5"])

emitted = err.getvalue()
assert code == 3, code
assert calls == [], calls
# Exit 3 and exit 4 differ in whether anything left the machine, and the egress
# line is what records the difference.
assert "cloud egress:" not in emitted, emitted
assert "credential-missing" in emitted, emitted
assert out.getvalue() == "", out.getvalue()
print("  credential-missing → exit 3, no egress line, no network: OK")
PY

echo "[5/11] every provider failure is exit 4 and says which state it was"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan
from hal import provider


class Fake:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return self.body


def envelope(text):
    return json.dumps({
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
    }).encode()


def run(urlopen):
    out, err = io.StringIO(), io.StringIO()
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("urllib.request.urlopen", urlopen):
            with redirect_stdout(out), redirect_stderr(err):
                code = code_plan.main(["--provider", "openai", "--repo", "mq-hal", "släpp v2.5"])
    return code, out.getvalue(), err.getvalue()


def raiser(exc):
    def go(*_a, **_k):
        raise exc
    return go


CASES = {
    provider.TRANSPORT_UNAVAILABLE: raiser(urllib.error.URLError("no route")),
    provider.PROVIDER_HTTP_ERROR: raiser(urllib.error.HTTPError(
        url="https://api.openai.com/v1/responses", code=429, msg="Too Many Requests",
        hdrs=None, fp=None)),
    provider.RESPONSE_INVALID: lambda *a, **k: Fake(envelope("not a plan")),
    provider.SCHEMA_INVALID: lambda *a, **k: Fake(envelope('{"goal": "x"}')),
}

for reason, urlopen in CASES.items():
    code, out, err = run(urlopen)
    assert code == 4, f"{reason} → exit {code}"
    # Coarse exit code, precise message: the operator can tell an unreachable
    # provider from one that answered badly without parsing anything.
    assert reason in err, f"{reason} not named in {err!r}"
    assert out == "", out
    # The attempt was made, so unlike credential-missing it is announced.
    assert err.count("cloud egress:") == 1, err

# Every failure state the transport can return has an exit code here. A new one
# added to hal/provider.py without a mapping is caught now, not in the field.
missing = [
    name for name, value in vars(provider).items()
    if name.isupper() and isinstance(value, str) and value.count("-") and value.islower()
    and value not in code_plan._EXIT_FOR_FAILURE and value != provider.OPENAI_BASE_URL
]
assert not missing, f"failure states with no exit code: {missing}"
print(f"  {len(CASES)} provider failures → exit 4, each named; all states mapped: OK")
PY

echo "[6/11] a plan that matches the schema is exit 0 and says who produced it"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan
import planner


class Fake:
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return json.dumps({
            "output": [{
                "type": "message",
                "content": [{"type": "output_text",
                             "text": json.dumps(planner.SAMPLE_PLAN)}],
            }]
        }).encode()


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("urllib.request.urlopen", lambda *a, **k: Fake()):
            with redirect_stdout(out), redirect_stderr(err):
                code = code_plan.main(argv)
    return code, out.getvalue(), err.getvalue()


code, out, err = run(["--provider", "openai", "--repo", "mq-hal", "släpp v2.5"])
assert code == 0, (code, err)
# Rule 6: a result always says which provider produced it. A cloud plan renders
# like a local one, so the screen has to carry the difference.
assert "Provider: openai (gpt-5.4-mini)" in out, out
assert planner.SAMPLE_PLAN["goal"] in out, out

# Rule 7: structured output on stdout, notices on stderr.
code, out, err = run(["--provider", "openai", "--repo", "mq-hal", "--json", "släpp v2.5"])
assert code == 0, (code, err)
payload = json.loads(out)
assert payload["ok"] is True and payload["provider"] == "openai", payload
assert payload["plan"] == planner.SAMPLE_PLAN, payload
assert "cloud egress:" in err and "cloud egress:" not in out
print("  exit 0, provider named, --json clean on stdout: OK")
PY

echo "[7/11] a plan the schema refuses never reaches the operator as a plan"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan
import planner

# B0 made these expressible; this is where that pays. Each is a plan the local
# format forbids, and none of them may be rendered as though it were one.
BROKEN = [
    {**planner.SAMPLE_PLAN, "risk": "banana"},
    {**planner.SAMPLE_PLAN, "affected_files": ["a.sh", 7]},
    {**planner.SAMPLE_PLAN, "steps": [{"id": 1, "description": "x"}]},
    {**planner.SAMPLE_PLAN, "rollback_plan": 5},
]

class Fake:
    def __init__(self, plan):
        self.plan = plan
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return json.dumps({
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(self.plan)}]}]
        }).encode()

for plan in BROKEN:
    out, err = io.StringIO(), io.StringIO()
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("urllib.request.urlopen", lambda *a, **k: Fake(plan)):
            with redirect_stdout(out), redirect_stderr(err):
                code = code_plan.main(["--provider", "openai", "--repo", "mq-hal", "x"])
    assert code == 4, (plan, code)
    assert "schema-invalid" in err.getvalue(), err.getvalue()
    assert out.getvalue() == "", out.getvalue()
print(f"  {len(BROKEN)} malformed plans → schema-invalid, nothing rendered: OK")
PY

echo "[8/11] what leaves is the instructions, one repo name and the goal"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

root = Path(sys.argv[1])
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, str(root))
import code_plan

captured = {}

class Fake:
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return b"not json"

def capture(request, timeout=None):
    captured["body"] = request.data
    return Fake()

GOAL = "stäng release-gaten i mq-hal"
with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with patch("urllib.request.urlopen", capture):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code_plan.main(["--provider", "openai", "--repo", "mq-hal", GOAL])

payload = json.loads(captured["body"].decode("utf-8"))
sent = json.loads(payload["input"])
assert sent == {"repo": "mq-hal", "goal": GOAL}, sent
assert payload["instructions"] == (root / "prompts" / "code-plan.txt").read_text()
assert payload["store"] is False, payload

# The earlier implementation sent the whole configured repo list with every
# request, describing the operator's working set to a third party as a side
# effect of asking about one repo. Naming one repo is not consent to name the
# rest, so every other configured name must be absent from the request.
body = captured["body"].decode("utf-8")
config = json.loads((root / "config" / "repos.json").read_text())
others = sorted(set(config.get("repos", {})) - {"mq-hal"})
assert others, "the fixture proves nothing if only one repo is configured"
leaked = [name for name in others if name in body]
assert not leaked, f"other configured repos left the machine: {leaked}"

# And no filesystem paths, absolute or relative to the operator's home.
for marker in (str(root), str(Path.home()), "/Users/"):
    assert marker not in body, f"a path left the machine: {marker}"

# The credential is a header, never the payload.
assert "sk-test" not in body
print(f"  request carries 1 repo name and the goal; {len(others)} other repos stayed home: OK")
PY

echo "[9/11] the egress line is announced before the transfer, once per request"
python3 - "$ROOT" <<'PY'
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan

seen = {}
err = io.StringIO()

def fake_urlopen(request, timeout=None):
    seen["stderr_before"] = err.getvalue()
    raise OSError("stop here")

with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with patch("urllib.request.urlopen", fake_urlopen):
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code_plan.main(["--provider", "openai", "--repo", "mq-hal", "x"])

line = [l for l in seen["stderr_before"].splitlines() if l.startswith("cloud egress:")]
assert len(line) == 1, seen["stderr_before"]
assert "kind=code-plan" in line[0], line[0]
assert "provider=openai" in line[0] and "model=gpt-5.4-mini" in line[0], line[0]
print(f"  announced before transfer: {line[0]}")
PY

echo "[10/11] the command surface documents cloud execution"
python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])

# Rule 2 is only satisfied if the documented surface names cloud execution.
# The check-command-docs gate proves the command is listed; this proves the
# listing says what the command does.
surface = (root / "docs" / "COMMAND_SURFACE.md").read_text()
detail = (root / "docs" / "hal-command-surface.md").read_text()

assert "`code-plan`" in surface, "code-plan missing from the registry"
assert "CLOUD_PROVIDER_BOUNDARY.md" in surface, "the registry does not point at the contract"
assert "### `code-plan`" in detail, "no reference section for code-plan"
for required in ("--provider", "sends data off the machine", "cloud egress:", "OPENAI_API_KEY"):
    assert required in detail, f"the reference does not mention {required!r}"
# The exit codes an operator scripts against.
for code in ("| 0 |", "| 2 |", "| 3 |", "| 4 |"):
    assert code in detail, f"exit code row {code} missing"
print("  cloud execution is named in both documented surfaces: OK")
PY

echo "[11/11] the schema sent to the provider narrows the local one, and only here"
python3 - "$ROOT" <<'PY'
import copy
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")
sys.path.insert(0, root)
import code_plan
import planner
from hal import provider

# OpenAI's strict mode refuses an object without additionalProperties: false,
# and requires every declared property to be listed in required. The local plan
# format is not written to those rules and must not be edited to satisfy a
# remote validator, so the adjustment lives in the cloud command.
before = copy.deepcopy(planner.PLAN_SCHEMA)
strict = code_plan.strict_schema(planner.PLAN_SCHEMA)
assert planner.PLAN_SCHEMA == before, "the local plan format was mutated"


def objects(schema, path="schema"):
    if isinstance(schema, dict):
        if isinstance(schema.get("properties"), dict):
            yield path, schema
        for name, sub in (schema.get("properties") or {}).items():
            yield from objects(sub, f"{path}.properties.{name}")
        if isinstance(schema.get("items"), dict):
            yield from objects(schema["items"], f"{path}.items")


seen = 0
for path, obj in objects(strict):
    assert obj["additionalProperties"] is False, path
    assert obj["required"] == list(obj["properties"]), path
    seen += 1
assert seen >= 2, "the fixture must reach a nested object, not only the root"

# The transport still has to be able to verify what is asked for — B0's rule.
provider._check_schema(strict)

# Narrowing only: a document the provider is held to is still a plan by the
# local definition. The reverse is not claimed and is not true.
assert provider.conforms(planner.SAMPLE_PLAN, strict), "SAMPLE_PLAN fails the strict form"
loose = {**planner.SAMPLE_PLAN,
         "steps": [{"id": 1, "description": "x", "requires_confirm": False}]}
assert provider.conforms(loose, planner.PLAN_SCHEMA), "fixture is not loose-but-valid"
assert not provider.conforms(loose, strict), "the strict form must be strictly narrower"

# And it is the strict form that actually goes out.
captured = {}


class Fake:
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return b"not json"


def capture(request, timeout=None):
    captured["body"] = request.data
    return Fake()


with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with patch("urllib.request.urlopen", capture):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code_plan.main(["--provider", "openai", "--repo", "mq-hal", "x"])

sent = json.loads(captured["body"].decode("utf-8"))["text"]["format"]
assert sent["strict"] is True, sent
for path, obj in objects(sent["schema"]):
    assert obj["additionalProperties"] is False, f"sent schema is not strict at {path}"
print(f"  {seen} objects narrowed, local format untouched, strict form sent: OK")
PY

echo "OK: mq-hal code-plan smoke test passed"
