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

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

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
}


def conforms(document: Any, schema: dict[str, Any]) -> bool:
    """Check a document against the subset of JSON Schema this module requests.

    Not a general validator: it covers `type`, `properties`, `required` and
    `additionalProperties`, which is what the strict json_schema requests here
    are built from. A schema using anything else is checked less strictly than
    it reads, so keep requests inside this subset.
    """
    expected = schema.get("type")
    if expected in _JSON_TYPES:
        if expected == "boolean":
            if not isinstance(document, bool):
                return False
        elif expected in {"number", "integer"}:
            if isinstance(document, bool) or not isinstance(document, _JSON_TYPES[expected]):
                return False
        elif not isinstance(document, _JSON_TYPES[expected]):
            return False

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

    return ProviderResult(
        ok=True,
        provider=selection.provider,
        model=selection.model,
        failure_reason=None,
        response=document if isinstance(document, dict) else None,
    )
