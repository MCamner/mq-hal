#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: cloud provider boundary"

echo "[1/19] syntax check"
python3 -m py_compile "$ROOT/hal/provider.py"

echo "[2/19] a missing credential fails before any network I/O or egress"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

calls = []
buffer = io.StringIO()
with patch.dict("os.environ", {}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: calls.append(1)):
        with patch.object(sys, "stderr", buffer):
            result = provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions="none",
                input_text="none",
                schema={"type": "object", "properties": {}, "required": []},
                schema_name="t",
            )

assert result.ok is False, result
assert result.failure_reason == provider.CREDENTIAL_MISSING, result
assert result.response is None, result
assert calls == [], f"credential-missing must not reach the network: {calls}"
assert buffer.getvalue() == "", f"credential-missing must emit no egress line: {buffer.getvalue()!r}"
print("  credential-missing → 0 network calls, 0 egress lines: OK")
PY

echo "[3/19] an HTTP error is a provider error, not a transport failure"
python3 - "$ROOT" <<'PY'
import io
import sys
import urllib.error
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

def raise_http(*_a, **_k):
    raise urllib.error.HTTPError(
        url="https://api.openai.com/v1/responses",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
    with patch("urllib.request.urlopen", raise_http):
        with patch.object(sys, "stderr", io.StringIO()):
            result = provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions="none",
                input_text="none",
                schema={"type": "object", "properties": {}, "required": []},
                schema_name="t",
            )

# HTTPError subclasses URLError, which subclasses OSError. Catching either of
# the broader classes first silently turns every 4xx/5xx into a transport
# failure, and the operator is told the network is down when the provider
# answered.
assert result.failure_reason == provider.PROVIDER_HTTP_ERROR, (
    f"HTTP 500 must be {provider.PROVIDER_HTTP_ERROR}, got {result.failure_reason}"
)
assert result.ok is False and result.response is None
print("  HTTP 500 → provider-http-error: OK")
PY

echo "[4/19] DNS, socket and timeout failures are transport failures"
python3 - "$ROOT" <<'PY'
import io
import socket
import sys
import urllib.error
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

def attempt(exc):
    def raiser(*_a, **_k):
        raise exc
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
        with patch("urllib.request.urlopen", raiser):
            with patch.object(sys, "stderr", io.StringIO()) as buffer:
                result = provider.run_request(
                    provider.select_provider("openai", "gpt-test"),
                    kind="unit-test",
                    instructions="none",
                    input_text="none",
                    schema={"type": "object", "properties": {}, "required": []},
                    schema_name="t",
                )
                return result, buffer.getvalue()

for exc in (
    urllib.error.URLError(socket.gaierror("nodename nor servname provided")),
    TimeoutError("timed out"),
    OSError("connection reset"),
):
    result, emitted = attempt(exc)
    assert result.failure_reason == provider.TRANSPORT_UNAVAILABLE, (
        f"{type(exc).__name__} → {result.failure_reason}"
    )
    # The attempt was made, so unlike credential-missing this one is announced.
    assert emitted.count("cloud egress:") == 1, emitted
print("  transport failures → transport-unavailable, 1 egress line each: OK")
PY

echo "[5/19] unparseable and schema-breaking answers are different failures"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}

class Fake:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return self.body

def answer(body):
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
        with patch("urllib.request.urlopen", lambda *a, **k: Fake(body)):
            with patch.object(sys, "stderr", io.StringIO()):
                return provider.run_request(
                    provider.select_provider("openai", "gpt-test"),
                    kind="unit-test",
                    instructions="none",
                    input_text="none",
                    schema=SCHEMA,
                    schema_name="t",
                )

def envelope(text):
    return json.dumps({
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
    }).encode()

assert answer(b"not json at all").failure_reason == provider.RESPONSE_INVALID
assert answer(envelope("still not json")).failure_reason == provider.RESPONSE_INVALID
assert answer(envelope('{"ok": "yes"}')).failure_reason == provider.SCHEMA_INVALID
assert answer(envelope('{"ok": true, "extra": 1}')).failure_reason == provider.SCHEMA_INVALID
assert answer(envelope('{}')).failure_reason == provider.SCHEMA_INVALID
print("  response-invalid and schema-invalid stay apart: OK")
PY

echo "[6/19] a successful request reports which provider produced it"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}

class Fake:
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return json.dumps({
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"ok": true}'}],
            }]
        }).encode()

with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: Fake()):
        with patch.object(sys, "stderr", io.StringIO()):
            result = provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions="none",
                input_text="none",
                schema=SCHEMA,
                schema_name="t",
            )

assert result.ok is True, result
assert result.failure_reason is None, result
assert result.response == {"ok": True}, result
assert result.provider == "openai" and result.model == "gpt-test", result
print("  success carries provider, model and response: OK")
PY

echo "[7/19] the egress line counts the exact bytes handed to the transport"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

captured = {}

class Fake:
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return b"not json"

def fake_urlopen(request, timeout=None):
    captured["body"] = request.data
    return Fake()

# Non-ASCII on purpose: character length and UTF-8 byte length differ, and a
# byte count taken from the string would quietly understate what left.
text = "återställ mängden — naïve café 日本語"

buffer = io.StringIO()
with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
    with patch("urllib.request.urlopen", fake_urlopen):
        with patch.object(sys, "stderr", buffer):
            provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions="none",
                input_text=text,
                schema={"type": "object", "properties": {}, "required": []},
                schema_name="t",
            )

line = buffer.getvalue().strip()
body = captured["body"]
assert isinstance(body, bytes), type(body)
declared = int(line.split("bytes=")[1].split()[0])
assert declared == len(body), f"declared {declared} != {len(body)} bytes sent"
print(f"  bytes={declared} equals the request body handed to transport: OK")
PY

echo "[8/19] the egress line is written before any network I/O"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

buffer = io.StringIO()
seen_before_call = {}

def fake_urlopen(request, timeout=None):
    seen_before_call["stderr"] = buffer.getvalue()
    raise OSError("stop here")

with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
    with patch("urllib.request.urlopen", fake_urlopen):
        with patch.object(sys, "stderr", buffer):
            provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions="none",
                input_text="none",
                schema={"type": "object", "properties": {}, "required": []},
                schema_name="t",
            )

assert "cloud egress:" in seen_before_call["stderr"], (
    "the operator must know a transfer is about to be attempted, not that one "
    f"was: {seen_before_call['stderr']!r}"
)
print("  egress announced before transfer: OK")
PY

echo "[9/19] one egress line per request, not per process"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

buffer = io.StringIO()
with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))):
        with patch.object(sys, "stderr", buffer):
            for model in ("gpt-one", "gpt-two", "gpt-three"):
                provider.run_request(
                    provider.select_provider("openai", model),
                    kind="unit-test",
                    instructions="none",
                    input_text="none",
                    schema={"type": "object", "properties": {}, "required": []},
                    schema_name="t",
                )

lines = [l for l in buffer.getvalue().splitlines() if l.startswith("cloud egress:")]
assert len(lines) == 3, lines
assert "model=gpt-two" in lines[1], lines
print("  3 requests → 3 egress lines, each naming its own model: OK")
PY

echo "[10/19] the egress line carries no credential and no payload content"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

secret = "sk-do-not-print-me"
prompt = "PRIVATE-REPO-CONTENT-MARKER"
buffer = io.StringIO()

with patch.dict("os.environ", {"OPENAI_API_KEY": secret}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))):
        with patch.object(sys, "stderr", buffer):
            provider.run_request(
                provider.select_provider("openai", "gpt-test"),
                kind="unit-test",
                instructions=f"instructions {prompt}",
                input_text=f"input {prompt}",
                schema={"type": "object", "properties": {}, "required": []},
                schema_name="t",
            )

emitted = buffer.getvalue()
assert secret not in emitted, "credential leaked into the egress line"
assert prompt not in emitted, "payload content leaked into the egress line"
for field in ("provider=", "model=", "kind=", "bytes="):
    assert field in emitted, f"{field} missing from {emitted!r}"
print("  egress line is metadata only: OK")
PY

echo "[11/19] selection is explicit; the transport chooses no provider"
python3 - "$ROOT" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from hal import provider

# An unnamed or unknown provider is not a request that may be attempted.
for bad in ("", "ollama-ish", "anthropic", None):
    try:
        provider.select_provider(bad, "gpt-test")
    except ValueError:
        continue
    raise AssertionError(f"select_provider accepted {bad!r}")

# Rule 8: the transport executes an already-selected request. If run_request
# could reach the profile configuration, the client would be choosing policy.
source = (root / "hal" / "provider.py").read_text()
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "run_request":
        names = {
            n.id for n in ast.walk(node) if isinstance(n, ast.Name)
        } | {
            n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
        }
        forbidden = names & {
            "load_model_profiles", "profile_for_name", "model_for_profile",
            "select_provider", "CONFIG_PATH",
        }
        assert not forbidden, f"run_request reaches selection policy: {forbidden}"
        break
else:
    raise AssertionError("run_request not found")
print("  selection refuses unnamed providers; transport holds no policy: OK")
PY

echo "[12/19] a local command cannot become a cloud command through config"
python3 - "$ROOT" <<'PY'
import ast
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])

# Rule 1 is structural. The local-first commands must not import the provider
# module at all, so no configuration change can move their trust boundary.
LOCAL = ["scripts/hal.py", "scripts/planner.py", "scripts/critic.py"]
for relative in LOCAL:
    tree = ast.parse((root / relative).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {f"{node.module}.{a.name}" for a in node.names}
    reaching = {name for name in imported if "provider" in name}
    assert not reaching, f"{relative} reaches the cloud boundary: {reaching}"

# And the profile configuration carries no provider switch to flip.
profiles = json.loads((root / "config" / "models.json").read_text())["profiles"]
carrying = {name for name, p in profiles.items() if "provider" in p}
assert not carrying, f"config/models.json can select a provider: {carrying}"
print(f"  {len(LOCAL)} local commands hold no provider import; config has no switch: OK")
PY

echo "[13/19] the destination is fixed in code; the environment cannot move it"
python3 - "$ROOT" <<'PY'
import io
import os
import sys
from unittest.mock import patch

# Set before the import: the module reads its destination at import time, so a
# test that imports first would prove nothing about an env-settable constant.
os.environ["OPENAI_BASE_URL"] = "https://attacker.example/v1"
os.environ["OPENAI_API_KEY"] = "sk-test"

sys.path.insert(0, sys.argv[1])
from hal import provider

seen = []

class Answer:
    def read(self):
        return b'{"output": [{"type": "message", "content": [{"type": "output_text", "text": "{\\"ok\\": true}"}]}]}'
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

def capture(request, *a, **k):
    seen.append(request.full_url)
    return Answer()

with patch("urllib.request.urlopen", capture):
    with patch.object(sys, "stderr", io.StringIO()):
        provider.run_request(
            provider.select_provider("openai", "gpt-test"),
            kind="unit-test",
            instructions="none",
            input_text="none",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="t",
        )

assert seen, "no request was made"
# Rule 2: changing configuration is not consent to data egress. A credential
# must not be redirectable to another host while the egress line still says
# provider=openai.
assert seen[0].startswith("https://api.openai.com/v1/"), (
    f"OPENAI_BASE_URL moved the credential to {seen[0]}"
)
assert "attacker.example" not in seen[0], seen[0]
print(f"  destination stayed {seen[0]}: OK")
PY


echo "[14/19] a schema this module cannot verify is refused before egress"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

calls = []
buffer = io.StringIO()

# Each of these reads as a constraint the module does not check. Announcing and
# sending one would claim an enforcement that never happens, and a response
# violating it would come back marked valid.
REFUSED = [
    # The result type carries a dict; an array or a string answer has nowhere
    # to go even when it is valid.
    {"type": "array", "items": {"type": "string"}},
    {"type": "string"},
    # A keyword conforms() has never heard of.
    {"type": "object", "anyOf": [{"required": ["a"]}]},
    # items is applied to array elements and to nothing else. Written where no
    # array can appear it constrains nothing.
    {"type": "object", "properties": {"tags": {"type": "string", "items": {"type": "string"}}}},
    {"type": "object", "properties": {"tags": {"items": {"type": "string"}}}},
    # A per-position items list is a different rule; this module applies one
    # subschema to every element.
    {"type": "object", "properties": {"tags": {"type": "array", "items": [{"type": "string"}]}}},
    # An enum nothing can satisfy, and one whose members are compared as
    # something other than the JSON scalars conforms() compares.
    {"type": "object", "properties": {"mode": {"type": "string", "enum": []}}},
    {"type": "object", "properties": {"mode": {"type": "string", "enum": "low"}}},
    {"type": "object", "properties": {"mode": {"enum": [{"a": 1}]}}},
    # A union widens to whatever it holds, so an unknown member widens it to
    # everything.
    {"type": "object", "properties": {"x": {"type": ["string", "date"]}}},
    {"type": "object", "properties": {"x": {"type": []}}},
    # The unverified subschema is one level down, where the recursion has to
    # reach it.
    {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {"type": "object", "properties": {"id": {"type": "date"}}},
            }
        },
    },
]

with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: calls.append(1)):
        with patch.object(sys, "stderr", buffer):
            for schema in REFUSED:
                try:
                    provider.run_request(
                        provider.select_provider("openai", "gpt-test"),
                        kind="unit-test",
                        instructions="none",
                        input_text="none",
                        schema=schema,
                        schema_name="t",
                    )
                except ValueError:
                    continue
                raise AssertionError(f"schema was accepted but is not verified: {schema}")

assert calls == [], f"a refused schema must not reach the network: {calls}"
assert buffer.getvalue() == "", f"a refused schema must emit no egress line: {buffer.getvalue()!r}"

# The supported subset still goes through, and a top-level object result is
# what `response: dict | None` promises.
ACCEPTED = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
    "description": "annotations constrain nothing, so they stay allowed",
}
provider._check_schema(ACCEPTED)
print(f"  {len(REFUSED)} unverifiable schemas refused, no egress, no network: OK")
PY

echo "[15/19] a keyword value outside what conforms() enforces is refused too"
python3 - "$ROOT" <<'PY'
import io
import sys
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
from hal import provider

calls = []
buffer = io.StringIO()

# Allowing the keyword is not the same as understanding its value. Each schema
# below uses only permitted keywords, but carries a value conforms() cannot act
# on, so it would read as a constraint that is never enforced.
REFUSED = [
    # required as a string iterates per character, asking for keys nobody wrote.
    {"type": "object", "properties": {}, "required": "field"},
    {"type": "object", "properties": {}, "required": [1]},
    # Only False is read as a restriction; a subschema here constrains nothing.
    {"type": "object", "properties": {}, "additionalProperties": {"type": "string"}},
    # properties is walked as a mapping of name to subschema.
    {"type": "object", "properties": ["a", "b"]},
]

with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with patch("urllib.request.urlopen", lambda *a, **k: calls.append(1)):
        with patch.object(sys, "stderr", buffer):
            for schema in REFUSED:
                try:
                    provider.run_request(
                        provider.select_provider("openai", "gpt-test"),
                        kind="unit-test",
                        instructions="none",
                        input_text="none",
                        schema=schema,
                        schema_name="t",
                    )
                except ValueError:
                    continue
                raise AssertionError(f"schema value was accepted but is not enforced: {schema}")

assert calls == [], f"a refused schema must not reach the network: {calls}"
assert buffer.getvalue() == "", f"a refused schema must emit no egress line: {buffer.getvalue()!r}"

# Every type conforms() implements stays usable as a nested value, alone and
# inside a union.
for name in ["object", "array", "string", "number", "integer", "boolean", "null"]:
    provider._check_schema(
        {"type": "object", "properties": {"x": {"type": name}}, "required": ["x"],
         "additionalProperties": False}
    )
    provider._check_schema(
        {"type": "object", "properties": {"x": {"type": [name, "null"]}}}
    )
print(f"  {len(REFUSED)} unenforceable keyword values refused; 7 supported types still pass: OK")
PY

echo "[16/19] the plan format is expressible: every shipped PLAN_SCHEMA verifies"
python3 - "$ROOT" <<'PY'
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
# The provider package first: `scripts/hal.py` would shadow the `hal` package
# if the scripts directory led the path.
from hal import provider  # noqa: E402

sys.path.insert(0, str(root / "scripts"))
import planner  # noqa: E402
import fix_planner  # noqa: E402

# The point of the capability. These schemas are the ones mq-hal already asks
# local models for; if the boundary cannot verify them, a cloud request could
# only be made by asking for less than the caller needs.
for name, schema in (
    ("scripts/planner.py", planner.PLAN_SCHEMA),
    ("scripts/fix_planner.py", fix_planner.PLAN_SCHEMA),
):
    provider._check_schema(schema)
    print(f"  {name} PLAN_SCHEMA verifies")

assert provider.conforms(planner.SAMPLE_PLAN, planner.PLAN_SCHEMA), planner.SAMPLE_PLAN

# And it holds at the boundary, not only in the helper: a plan that breaks the
# schema comes back as schema-invalid rather than ok.
class Fake:
    def __init__(self, text):
        self.text = text
    def __enter__(self):
        return self
    def __exit__(self, *_a):
        return False
    def read(self):
        return json.dumps({
            "output": [{"type": "message", "content": [{"type": "output_text", "text": self.text}]}]
        }).encode()

def answer(plan):
    text = json.dumps(plan)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("urllib.request.urlopen", lambda *a, **k: Fake(text)):
            with patch.object(sys, "stderr", io.StringIO()):
                return provider.run_request(
                    provider.select_provider("openai", "gpt-test"),
                    kind="unit-test",
                    instructions="none",
                    input_text="none",
                    schema=planner.PLAN_SCHEMA,
                    schema_name="plan",
                )

good = answer(planner.SAMPLE_PLAN)
assert good.ok is True, good
assert good.response == planner.SAMPLE_PLAN, good

# risk outside the enum, a non-string among the file names, and a step missing
# a required field: each is a constraint A1 could not express at all.
for mutate in (
    lambda p: {**p, "risk": "banana"},
    lambda p: {**p, "affected_files": ["a.sh", 7]},
    lambda p: {**p, "steps": [{"id": 1, "description": "x"}]},
    lambda p: {**p, "steps": [{**p["steps"][0], "safe_command": 5}]},
):
    broken = mutate(json.loads(json.dumps(planner.SAMPLE_PLAN)))
    result = answer(broken)
    assert result.failure_reason == provider.SCHEMA_INVALID, (broken, result)

print("  SAMPLE_PLAN accepted; 4 plan violations → schema-invalid: OK")
PY

echo "[17/19] the subset is checked as written: items, enum, null and unions"
python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(sys.argv[1]) / "tests"))
from provider_schema_corpus import CORPUS  # noqa: E402
from hal import provider

failures = [
    f"{name}: expected {expected}, got {provider.conforms(document, schema)}"
    for name, document, schema, expected in CORPUS
    if provider.conforms(document, schema) is not expected
]
assert not failures, "\n".join(failures)
print(f"  {len(CORPUS)} documents judged as written: OK")
PY

echo "[18/19] the corpus catches a check that stops checking"
python3 - "$ROOT" <<'PY'
import sys
import types
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "tests"))
from provider_schema_corpus import CORPUS  # noqa: E402

SOURCE = (root / "hal" / "provider.py").read_text()

def load(anchor=None, replacement=None):
    source = SOURCE
    if anchor is not None:
        assert source.count(anchor) == 1, f"mutation anchor is not unique: {anchor!r}"
        source = source.replace(anchor, replacement)
    module = types.ModuleType("provider_mutant")
    # @dataclass resolves annotations through sys.modules, so the copy has to
    # be registered before its body runs.
    sys.modules["provider_mutant"] = module
    try:
        exec(compile(source, "provider_mutant.py", "exec"), module.__dict__)
    finally:
        del sys.modules["provider_mutant"]
    return module

# A test suite that cannot tell a working check from a removed one is not
# evidence that the check works. Each mutation below silently drops one of the
# three capabilities B0 adds; at least one corpus case has to notice.
MUTATIONS = {
    "items is ignored": (
        "    return all(conforms(element, items) for element in document)",
        "    return True",
    ),
    "enum is ignored": (
        'if "enum" in schema and not _enum_allows(document, schema["enum"]):',
        'if "enum" in schema and False:',
    ),
    "null accepts any value": (
        '"null": type(None),',
        '"null": object,',
    ),
}

baseline = load()
alive = [
    name for name, document, schema, expected in CORPUS
    if baseline.conforms(document, schema) is not expected
]
assert not alive, f"the unmutated module already disagrees with the corpus: {alive}"

for name, (anchor, replacement) in MUTATIONS.items():
    mutant = load(anchor, replacement)
    caught = [
        case for case, document, schema, expected in CORPUS
        if mutant.conforms(document, schema) is not expected
    ]
    assert caught, f"mutation survived the corpus: {name}"
    print(f"  {name} → caught by {len(caught)} case(s)")

print(f"  {len(MUTATIONS)} mutations killed: OK")
PY

echo "[19/19] an allowed keyword is one conforms() actually reads"
python3 - "$ROOT" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from hal import provider

# The recurring failure this module has already had twice: a keyword reaches
# the allowlist and conforms() never learns to read it, so the request asks for
# an enforcement that does not happen. SCHEMA_KEYWORDS, the keyword values
# _check_schema admits, and conforms() change together or not at all.
ANNOTATIONS = {"title", "description"}
READERS = {"conforms", "_items_conform", "_enum_allows", "_type_matches", "_is_json_type"}

tree = ast.parse((root / "hal" / "provider.py").read_text())
read_names: set[str] = set()
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in READERS:
        read_names |= {
            n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }

enforced = set(provider.SCHEMA_KEYWORDS) - ANNOTATIONS
missing = sorted(enforced - read_names)
assert not missing, (
    f"SCHEMA_KEYWORDS allows {missing}, which no function in {sorted(READERS)} "
    f"reads — the request would claim a check nothing performs"
)

# And the types _check_schema admits are the types conforms() can test.
for name in provider._JSON_TYPES:
    assert provider._is_json_type(None, name) is (name == "null"), name
print(f"  {len(enforced)} allowed keywords are read by conforms(): OK")
PY

echo "OK: cloud provider boundary smoke test passed"
