"""Documents whose verdict the provider schema subset has to get right.

Shared by two steps of `provider-boundary-smoke.sh`: one runs them against
`hal/provider.py` as it is, the other against deliberately broken copies of it.
The second step is what makes the first mean anything — a corpus that passes
whether or not the check runs is not evidence that the check runs.

Each entry is `(name, document, schema, expected)`.
"""
from __future__ import annotations

from typing import Any

STRINGS: dict[str, Any] = {"type": "array", "items": {"type": "string"}}

RISK: dict[str, Any] = {"type": "string", "enum": ["low", "medium", "high", "unknown"]}

NULLABLE: dict[str, Any] = {"type": ["string", "null"]}

STEPS: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "description": {"type": "string"},
            "safe_command": {"type": ["string", "null"]},
            "requires_confirm": {"type": "boolean"},
        },
        "required": ["id", "description", "requires_confirm"],
    },
}

MATRIX: dict[str, Any] = {
    "type": "array",
    "items": {"type": "array", "items": {"type": "string"}},
}

CORPUS: list[tuple[str, Any, dict[str, Any], bool]] = [
    # items — an array is only as constrained as its elements.
    ("items: every element is a string", ["a", "b"], STRINGS, True),
    ("items: one element is not", ["a", 7], STRINGS, False),
    ("items: the empty array satisfies any element rule", [], STRINGS, True),
    ("items: a violation in last position still counts", ["a", "b", None], STRINGS, False),
    # enum — membership, and Python's bool/int overlap which JSON does not have.
    ("enum: a listed value", "low", RISK, True),
    ("enum: an unlisted value", "banana", RISK, False),
    ("enum: case is not membership", "LOW", RISK, False),
    ("enum: true is not 1", True, {"enum": [1]}, False),
    ("enum: 1 is not true", 1, {"enum": [True]}, False),
    # null and the union the plan format needs.
    ("union: null satisfies string|null", None, NULLABLE, True),
    ("union: a string satisfies string|null", "cat x", NULLABLE, True),
    ("union: a number satisfies neither", 123, NULLABLE, False),
    ("union: an array satisfies neither", ["x"], NULLABLE, False),
    ("null alone: only null", None, {"type": "null"}, True),
    ("null alone: not an empty string", "", {"type": "null"}, False),
    ("null alone: not zero", 0, {"type": "null"}, False),
    # Nested — the recursion has to reach a violation several levels down.
    (
        "nested: a well-formed step list",
        [
            {"id": 1, "description": "look", "safe_command": "ls", "requires_confirm": False},
            {"id": 2, "description": "decide", "safe_command": None, "requires_confirm": True},
        ],
        STEPS,
        True,
    ),
    (
        "nested: a step missing a required field",
        [{"id": 1, "description": "look"}],
        STEPS,
        False,
    ),
    (
        "nested: a step whose nullable field is a number",
        [{"id": 1, "description": "look", "safe_command": 5, "requires_confirm": False}],
        STEPS,
        False,
    ),
    (
        "nested: a step whose id is a boolean, not an integer",
        [{"id": True, "description": "look", "requires_confirm": False}],
        STEPS,
        False,
    ),
    ("nested: arrays inside arrays", [["a"], ["b", "c"]], MATRIX, True),
    ("nested: a violation two levels down", [["a"], ["b", 2]], MATRIX, False),
    # An object property carrying each of the three new rules at once.
    (
        "object: property rules apply through properties",
        {"risk": "high", "files": ["a.sh"], "rollback": None},
        {
            "type": "object",
            "properties": {"risk": RISK, "files": STRINGS, "rollback": NULLABLE},
            "required": ["risk", "files", "rollback"],
            "additionalProperties": False,
        },
        True,
    ),
    (
        "object: an enum violation inside a property",
        {"risk": "critical", "files": ["a.sh"], "rollback": None},
        {
            "type": "object",
            "properties": {"risk": RISK, "files": STRINGS, "rollback": NULLABLE},
            "required": ["risk", "files", "rollback"],
            "additionalProperties": False,
        },
        False,
    ),
    (
        "object: an items violation inside a property",
        {"risk": "high", "files": ["a.sh", 3], "rollback": None},
        {
            "type": "object",
            "properties": {"risk": RISK, "files": STRINGS, "rollback": NULLABLE},
            "required": ["risk", "files", "rollback"],
            "additionalProperties": False,
        },
        False,
    ),
    (
        "object: a null violation inside a property",
        {"risk": "high", "files": ["a.sh"], "rollback": 0},
        {
            "type": "object",
            "properties": {"risk": RISK, "files": STRINGS, "rollback": NULLABLE},
            "required": ["risk", "files", "rollback"],
            "additionalProperties": False,
        },
        False,
    ),
    # The rules A1 already had must keep working alongside the new ones.
    ("object: a missing required property", {}, {"type": "object", "required": ["ok"]}, False),
    (
        "object: an unexpected property under additionalProperties false",
        {"ok": True, "extra": 1},
        {"type": "object", "properties": {"ok": {"type": "boolean"}}, "additionalProperties": False},
        False,
    ),
    ("scalar: a string is not an object", "text", {"type": "object"}, False),
]
