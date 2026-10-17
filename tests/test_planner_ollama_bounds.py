"""Regression tests for bounded local Ollama planning."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import planner


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


def test_planner_sends_bounded_request():
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse({
            "response": '{"goal":"test","steps":[]}'
        })

    with patch.object(
        planner.urllib.request,
        "urlopen",
        side_effect=fake_urlopen,
    ):
        result = planner.call_ollama(
            "test",
            {"repos": {}, "default_repo": "mq-hal"},
            model="qwen3.5:9b",
        )

    payload = captured["payload"]

    assert result is not None
    assert json.loads(result)["goal"] == "test"
    assert payload["model"] == "qwen3.5:9b"
    assert payload["think"] is False
    assert payload["stream"] is False
    assert payload["options"]["num_predict"] == 1024
    assert payload["options"]["temperature"] == 0
    assert payload["format"] == planner.PLAN_SCHEMA
    assert captured["timeout"] > 0


def test_planner_handles_timeout():
    with patch.object(
        planner.urllib.request,
        "urlopen",
        side_effect=TimeoutError("timed out"),
    ):
        result = planner.call_ollama(
            "test",
            {"repos": {}},
            model="qwen3.5:9b",
        )

    assert result is None


def test_planner_handles_invalid_json():
    with patch.object(
        planner.urllib.request,
        "urlopen",
        return_value=FakeResponse({"response": "{}"}),
    ):
        result = planner.call_ollama(
            "test",
            {"repos": {}},
            model="qwen3.5:9b",
        )

    assert result == "{}"
