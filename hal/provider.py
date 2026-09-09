"""Transport for an already-selected external model provider.

`mq-hal` is local-first. Everything here exists to make one thing true: a
request to a provider outside this machine is a deliberate act, visible before
it happens, and its failures are told apart from each other.

The contract is `docs/CLOUD_PROVIDER_BOUNDARY.md`. Two rules from it shape
this module:

    Network egress is a command-surface decision, not a model-profile
    side effect.

    A failed provider never silently becomes another provider.

So `select_provider` decides *what* is being asked, `run_request` only carries
it out, and nothing here reads model-profile configuration — a config edit
cannot move a trust boundary that configuration never held.

Failures do not collapse. A missing credential is not an offline laptop, an
offline laptop is not a provider that answered with an error, and a provider
that answered is not one whose answer was usable. `ProviderResult` keeps them
apart, and the caller decides what to do — this module never substitutes a
local result for a cloud one.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

CREDENTIAL_MISSING = "credential-missing"
TRANSPORT_UNAVAILABLE = "transport-unavailable"
PROVIDER_HTTP_ERROR = "provider-http-error"
RESPONSE_INVALID = "response-invalid"
SCHEMA_INVALID = "schema-invalid"

# Fixed in code, deliberately not read from the environment. Rule 2 of the
# contract says changing configuration is not consent to data egress, and an
# env-settable base URL would break that quietly: the credential would follow
# the new host while the egress line still announced `provider=openai`. A
# proxy, an Azure deployment or any OpenAI-compatible endpoint is a different
# destination and belongs to its own named provider, not to this one.
OPENAI_BASE_URL = "https://api.openai.com/v1"

SUPPORTED_PROVIDERS = {"openai"}
CREDENTIAL_ENV = {"openai": "OPENAI_API_KEY"}


@dataclass(frozen=True)
class Selection:
    """One provider request, chosen before any transport runs."""

    provider: str
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    provider: str
    model: str
    failure_reason: str | None
    response: dict[str, Any] | None


def select_provider(
    provider: Any, model: Any, reasoning_effort: str = "medium"
) -> Selection:
    """Name a provider explicitly, or get nothing.

    There is no default and no configuration lookup. A caller that cannot say
    which provider it means has not expressed operator intent, and an unnamed
    request is not one this module will carry.
    """
    if not isinstance(provider, str) or provider not in SUPPORTED_PROVIDERS:
        known = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ValueError(f"unknown provider: {provider!r}. Known providers: {known}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"provider {provider!r} selected without a model")
    return Selection(
        provider=provider, model=model.strip(), reasoning_effort=reasoning_effort
    )


def _fail(selection: Selection, reason: str) -> ProviderResult:
    return ProviderResult(
        ok=False,
        provider=selection.provider,
        model=selection.model,
        failure_reason=reason,
        response=None,
    )


def _request_body(
    selection: Selection,
    instructions: str,
    input_text: str,
    schema: dict[str, Any],
    schema_name: str,
    max_output_tokens: int,
) -> bytes:
    payload = {
        "model": selection.model,
        "instructions": instructions,
        "input": input_text,
        "reasoning": {"effort": selection.reasoning_effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
        "max_output_tokens": max_output_tokens,
        # The provider is asked not to retain the request.
        "store": False,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _announce(selection: Selection, kind: str, body: bytes) -> None:
    """Say what is about to leave, before it leaves.

    Metadata only: the operator learns that a transfer is being attempted and
    how large it is, without the prompt, the paths or the credential being
    written anywhere. One line per request — a notice emitted once per process
    would describe the first transfer and conceal every later one.
    """
    print(
        f"cloud egress: provider={selection.provider} model={selection.model} "
        f"kind={kind} bytes={len(body)}",
        file=sys.stderr,
    )


def _output_text(envelope: dict[str, Any]) -> str | None:
    for item in envelope.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict) or content.get("type") != "output_text":
                continue
            value = content.get("text")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


_JSON_TYPES: dict[str, Any] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


# The keywords `conforms` implements, plus two that constrain nothing and so
# cost nothing to allow through.
SCHEMA_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "title",
        "description",
    }
)


def _check_type(declared: Any, path: str) -> set[str]:
    """Return the type names a subschema declares, or refuse the declaration.

    A union is a list of names — `["string", "null"]` is the one the plan
    format needs. Every member must be a type `conforms` can test, because a
    name it does not hold would be skipped and the union would widen silently
    to whatever the response happened to carry.
    """
    names = declared if isinstance(declared, list) else [declared]
    if isinstance(declared, list) and not names:
        raise ValueError(f"{path}.type is an empty union, which nothing satisfies")
    for name in names:
        if not isinstance(name, str) or name not in _JSON_TYPES:
            raise ValueError(
                f"{path}.type is {declared!r}, which this module cannot check. "
                f"Supported types: {', '.join(sorted(_JSON_TYPES))}"
            )
    return set(names)


def _check_schema(schema: Any, path: str = "schema") -> None:
    """Refuse a request this module could not honestly verify.

    The top level must be an object, because that is what the result type
    promises: `ProviderResult.response` is a `dict`, so a schema asking for an
    array or a string could succeed and still have nowhere to put its answer.

    Every keyword must be one `conforms` implements, and so must every keyword
    *value*. Permitting a keyword is not the same as understanding what was
    written in it: a `type` name `conforms` never tests, or an `items` sitting
    where no array can appear, reads as a constraint the module enforces and is
    not. Refusing both keeps the request and the check in step — what is asked
    for is what is verified.
    """
    if not isinstance(schema, dict):
        raise ValueError(f"{path} must be a JSON Schema object, got {type(schema).__name__}")

    unsupported = sorted(set(schema) - SCHEMA_KEYWORDS)
    if unsupported:
        raise ValueError(
            f"{path} uses JSON Schema keywords this module does not verify: "
            f"{', '.join(unsupported)}. Supported: {', '.join(sorted(SCHEMA_KEYWORDS))}"
        )

    # `conforms` looks each type name up in _JSON_TYPES and treats a miss as
    # "no match", so a name it does not hold must not get this far.
    declared_types: set[str] = set()
    if "type" in schema:
        declared_types = _check_type(schema["type"], path)

    # A string here would be iterated character by character, requiring keys
    # nobody asked for; a non-string entry could never match one.
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or not all(isinstance(n, str) for n in required):
            raise ValueError(f"{path}.required must be a list of property names")

    # Only False is read as a restriction. A subschema here would express one
    # that is never applied.
    if "additionalProperties" in schema:
        if not isinstance(schema["additionalProperties"], bool):
            raise ValueError(
                f"{path}.additionalProperties must be true or false; "
                f"a subschema there is not enforced"
            )

    # `conforms` compares enum members with `==`, which is total for JSON
    # scalars and nothing else here needs more. A container member would be
    # compared structurally, which is a different question than the one the
    # plan format asks.
    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, list) or not allowed:
            raise ValueError(f"{path}.enum must be a non-empty list of allowed values")
        for value in allowed:
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError(
                    f"{path}.enum holds a {type(value).__name__}; this module "
                    f"compares enum members as JSON scalars"
                )

    # `conforms` applies `items` to the elements of an array and to nothing
    # else. Written anywhere an array cannot appear it constrains nothing, so
    # it is refused rather than accepted and ignored.
    if "items" in schema:
        if "array" not in declared_types:
            raise ValueError(
                f"{path}.items is checked only for arrays, but {path}.type is "
                f"{schema.get('type')!r}; declare array where items is used"
            )
        items = schema["items"]
        if not isinstance(items, dict):
            raise ValueError(
                f"{path}.items must be one subschema for every element; a "
                f"per-position list is not applied"
            )
        _check_schema(items, f"{path}.items")

    if path == "schema" and schema.get("type") != "object":
        raise ValueError(
            f"schema must describe a top-level object, got type="
            f"{schema.get('type')!r}; ProviderResult.response carries a dict"
        )

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError(f"{path}.properties must be an object")
    for name, subschema in properties.items():
        _check_schema(subschema, f"{path}.properties.{name}")


def _is_json_type(document: Any, name: str) -> bool:
    expected = _JSON_TYPES.get(name)
    if expected is None:
        return False
    # JSON has no boolean/number overlap; Python does, and `True` would pass an
    # `integer` check unchallenged.
    if name == "boolean":
        return isinstance(document, bool)
    if name in {"number", "integer"}:
        return not isinstance(document, bool) and isinstance(document, expected)
    return isinstance(document, expected)


def _type_matches(document: Any, declared: Any) -> bool:
    names = declared if isinstance(declared, list) else [declared]
    return any(_is_json_type(document, name) for name in names)


def _enum_allows(document: Any, allowed: list[Any]) -> bool:
    for value in allowed:
        # `True == 1` in Python but not in JSON, so a boolean must not satisfy
        # a numeric member, nor a number a boolean one.
        if isinstance(value, bool) != isinstance(document, bool):
            continue
        if value == document:
            return True
    return False


def _items_conform(document: list[Any], schema: dict[str, Any]) -> bool:
    items = schema.get("items")
    if not isinstance(items, dict):
        return True
    return all(conforms(element, items) for element in document)


def conforms(document: Any, schema: dict[str, Any]) -> bool:
    """Check a document against the subset of JSON Schema this module requests.

    Not a general validator: it covers `type` (including a union such as
    `["string", "null"]`), `properties`, `required`, `additionalProperties`,
    `items` and `enum`. Requests are held to that same subset by
    `_check_schema`, so a schema reaching here never expresses more than this
    function checks.
    """
    if "type" in schema and not _type_matches(document, schema["type"]):
        return False

    if "enum" in schema and not _enum_allows(document, schema["enum"]):
        return False

    if isinstance(document, list):
        return _items_conform(document, schema)

    if not isinstance(document, dict):
        return True

    properties = schema.get("properties")
    properties = properties if isinstance(properties, dict) else {}
    for name in schema.get("required", []):
        if name not in document:
            return False
    if schema.get("additionalProperties") is False:
        if set(document) - set(properties):
            return False
    for name, value in document.items():
        subschema = properties.get(name)
        if isinstance(subschema, dict) and not conforms(value, subschema):
            return False
    return True

def run_request(
    selection: Selection,
    *,
    kind: str,
    instructions: str,
    input_text: str,
    schema: dict[str, Any],
    schema_name: str,
    timeout: int = 120,
    max_output_tokens: int = 4096,
) -> ProviderResult:
    """Carry out one already-selected provider request.

    The order is the contract's, and two of the steps are ordered for reasons
    that outlive this code: the credential is checked before anything is
    serialized or announced, so a missing key costs no transfer and leaves no
    egress line; and the announcement is written before the socket opens, so
    the line means "about to be attempted" rather than "was attempted".
    """
    # Before the credential check, and so before any egress: a schema outside
    # the verified subset is a malformed request, not a runtime failure state,
    # and it never becomes a `ProviderResult`.
    _check_schema(schema)

    env_var = CREDENTIAL_ENV[selection.provider]
    if not os.environ.get(env_var):
        return _fail(selection, CREDENTIAL_MISSING)

    body = _request_body(
        selection, instructions, input_text, schema, schema_name, max_output_tokens
    )
    _announce(selection, kind, body)

    request = urllib.request.Request(
        f"{OPENAI_BASE_URL.rstrip('/')}/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ[env_var]}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    # HTTPError first: it subclasses URLError, which subclasses OSError, so
    # catching either broader class above it turns every 4xx and 5xx into
    # "the network is unavailable" — telling the operator the transfer never
    # happened when in fact the provider answered.
    except urllib.error.HTTPError:
        return _fail(selection, PROVIDER_HTTP_ERROR)
    except (urllib.error.URLError, TimeoutError, OSError):
        return _fail(selection, TRANSPORT_UNAVAILABLE)

    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _fail(selection, RESPONSE_INVALID)
    if not isinstance(envelope, dict):
        return _fail(selection, RESPONSE_INVALID)

    text = _output_text(envelope)
    if text is None:
        return _fail(selection, RESPONSE_INVALID)
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return _fail(selection, RESPONSE_INVALID)

    if not conforms(document, schema):
        return _fail(selection, SCHEMA_INVALID)

    # `_check_schema` required a top-level object and `conforms` just held the
    # document to it, so this is a dict — `ok=True` can no longer arrive with an
    # empty response.
    return ProviderResult(
        ok=True,
        provider=selection.provider,
        model=selection.model,
        failure_reason=None,
        response=document,
    )
