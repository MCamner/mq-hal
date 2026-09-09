#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: cloud provider boundary"

echo "[1/12] syntax check"
python3 -m py_compile "$ROOT/hal/provider.py"

echo "[2/12] a missing credential fails before any network I/O or egress"
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

echo "[3/12] an HTTP error is a provider error, not a transport failure"
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

echo "[4/12] DNS, socket and timeout failures are transport failures"
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

echo "[5/12] unparseable and schema-breaking answers are different failures"
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

echo "[6/12] a successful request reports which provider produced it"
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

echo "[7/12] the egress line counts the exact bytes handed to the transport"
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

echo "[8/12] the egress line is written before any network I/O"
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

echo "[9/12] one egress line per request, not per process"
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

echo "[10/12] the egress line carries no credential and no payload content"
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

echo "[11/12] selection is explicit; the transport chooses no provider"
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

echo "[12/12] a local command cannot become a cloud command through config"
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

echo "OK: cloud provider boundary smoke test passed"
