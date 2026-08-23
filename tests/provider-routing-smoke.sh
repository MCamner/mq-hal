#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: hybrid model provider routing"

python3 - "$ROOT" <<'PY'
import json
import sys

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")

from model_profiles import profile_for_name

router = profile_for_name("router", default_profile="router")
planner = profile_for_name("planner", default_profile="planner")
critic = profile_for_name("critic", default_profile="critic")
code = profile_for_name("code", default_profile="code")

assert router["provider"] == "ollama", router
assert router["model"] == "qwen3:4b-instruct", router
for profile in (planner, critic, code):
    assert profile["provider"] == "openai", profile
    assert profile["model"].startswith("gpt-"), profile

print("  profile providers: OK")
PY

if "$ROOT/bin/mq-hal" --model planner --no-ai --raw-intent \
  "visa git status i mq-hal" >"$STATE_DIR/bad-provider.out" 2>&1; then
  echo "ERROR: router accepted an OpenAI-only profile" >&2
  exit 1
fi
grep -q "intent routing requires an Ollama profile" "$STATE_DIR/bad-provider.out"
echo "  router rejects cloud-only profiles: OK"

python3 - "$ROOT" <<'PY'
import json
import os
import sys
from unittest.mock import patch

root = sys.argv[1]
sys.path.insert(0, f"{root}/scripts")

import openai_client

class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps({
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"ok":true}'}],
            }]
        }).encode()

schema = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}

captured = {}
def fake_urlopen(request, timeout):
    captured["authorization"] = request.headers.get("Authorization")
    captured["payload"] = json.loads(request.data.decode())
    captured["timeout"] = timeout
    return FakeResponse()

with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-secret"}, clear=False):
    with patch("urllib.request.urlopen", fake_urlopen):
        result = openai_client.generate_structured(
            model="gpt-test",
            reasoning_effort="medium",
            instructions="Return JSON.",
            input_text="test",
            schema=schema,
            schema_name="test_result",
        )

assert result == '{"ok":true}', result
assert captured["authorization"] == "Bearer test-only-secret"
payload = captured["payload"]
assert payload["model"] == "gpt-test"
assert payload["store"] is False
assert payload["reasoning"] == {"effort": "medium"}
assert payload["text"]["format"]["type"] == "json_schema"
assert payload["text"]["format"]["strict"] is True
assert captured["timeout"] == 120

print("  OpenAI Responses contract: OK")
PY

echo "OK: hybrid model provider routing passed"
