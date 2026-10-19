"""Every local Ollama call turns thinking off explicitly.

qwen3.5 thinks by default; qwen3:4b-instruct, which these callers were written
against, did not. Measured on qwen3.5:9b with the intent schema: 46-80 s and
1,100-2,000 tokens with thinking on, 1.1 s and ~20 tokens with it off — and
model_test.py gives up after 30 s. planner.py already sends think=False
(test_planner_ollama_bounds.py); the other four did not.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import doctor_summary
import fix_planner
import hal
import model_test


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"response": "{}"}).encode("utf-8")


CALLERS = {
    "hal.call_ollama": (hal, lambda: hal.call_ollama("hitta OLLAMA_MODEL i mq-hal")),
    "doctor_summary.call_ollama_summary": (
        doctor_summary,
        lambda: doctor_summary.call_ollama_summary({}, "mq-hal", "mqlaunch doctor"),
    ),
    "fix_planner.call_ollama_plan": (fix_planner, lambda: fix_planner.call_ollama_plan({})),
    "model_test.call_model": (model_test, lambda: model_test.call_model("router")),
}


@pytest.mark.parametrize("name", sorted(CALLERS))
def test_ollama_call_sends_think_false(name):
    module, call = CALLERS[name]
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse()

    with patch.object(module.urllib.request, "urlopen", side_effect=fake_urlopen):
        try:
            call()
        except Exception:
            # Only the request matters here; "{}" is not a valid reply for
            # every caller, and how each one handles that is tested elsewhere.
            pass

    assert captured, f"{name} never called Ollama"
    assert captured["url"].endswith("/api/generate")
    assert captured["payload"].get("think") is False, (
        f"{name} does not send think=False: {captured['payload'].get('think')!r}"
    )
