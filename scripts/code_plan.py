#!/usr/bin/env python3
"""mq-hal code-plan: ask a named external provider for a plan.

This is the one command in `mq-hal` that leaves the machine, and it exists as a
separate command for that reason alone. `mq-hal plan` runs against local Ollama
through `scripts/planner.py` and cannot be made to do anything else; reaching a
provider means typing a different command with the provider named in it. The
trust boundary is a thing an operator types, not a field someone edits.

    mq-hal plan        → scripts/planner.py  → local Ollama
    mq-hal code-plan   → this file           → hal/provider.py → OpenAI

`docs/CLOUD_PROVIDER_BOUNDARY.md` is the contract. Three of its rules shape
this file:

    Network egress is a command-surface decision, not a model-profile
    side effect.

    A cloud request may occur only from a command or option whose documented
    command surface names cloud execution.

    A result must always say which provider produced it.

So `--provider` is required and has no default. There is nothing to configure
that would make this command reach a different destination, and nothing to
configure that would make any other command reach this one.

What leaves is the system instructions, the repository name the operator typed
and the goal the operator typed. Not the configured repo list, not the active
repo, not a path. The plan is asked for over a name, because the operator
naming one repository is not consent to describe the rest of their machine.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
# Ahead of this script's own directory, which holds `hal.py` and would
# otherwise be found first and shadow the `hal` package.
sys.path.insert(0, str(BASE_DIR))

from hal import provider  # noqa: E402
from planner import PLAN_SCHEMA, render  # noqa: E402

PROMPT_PATH = BASE_DIR / "prompts" / "code-plan.txt"

# Fixed here rather than read from config/models.json. Rule 1 of the contract
# is that a local command must not become a cloud command through
# configuration; the same reasoning applies in reverse, so this command's
# target is not something a config edit can move. `--model` changes it, in the
# same typed line that already names the provider.
DEFAULT_MODEL = "gpt-5.4-mini"

REQUEST_KIND = "code-plan"

# The contract's exit codes. Five failure states do not become five codes:
# shell policy stays coarse and the precise state stays in the result.
EXIT_OK = 0
EXIT_INVOCATION = 2
EXIT_CREDENTIAL = 3
EXIT_PROVIDER = 4

_EXIT_FOR_FAILURE = {
    provider.CREDENTIAL_MISSING: EXIT_CREDENTIAL,
    provider.TRANSPORT_UNAVAILABLE: EXIT_PROVIDER,
    provider.PROVIDER_HTTP_ERROR: EXIT_PROVIDER,
    provider.RESPONSE_INVALID: EXIT_PROVIDER,
    provider.SCHEMA_INVALID: EXIT_PROVIDER,
}

_FAILURE_TEXT = {
    provider.CREDENTIAL_MISSING: (
        "no credential available. OPENAI_API_KEY is read from the process "
        "environment; mq-hal does not read the Keychain itself"
    ),
    provider.TRANSPORT_UNAVAILABLE: "the provider could not be reached",
    provider.PROVIDER_HTTP_ERROR: "the provider answered with an HTTP error",
    provider.RESPONSE_INVALID: "the provider's answer could not be parsed",
    provider.SCHEMA_INVALID: "the provider's answer did not match the plan schema",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mq-hal code-plan",
        description=(
            "Ask a named external provider for a plan. This command sends the "
            "repository name and the goal to that provider."
        ),
    )
    # required=True and no default, in both cases on purpose. A provider that
    # can be omitted is a provider that can be assumed, and an operator who
    # did not name a repository has not chosen what to describe to it.
    parser.add_argument(
        "--provider",
        required=True,
        choices=sorted(provider.SUPPORTED_PROVIDERS),
        help="External provider to send this request to. No default.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        metavar="NAME",
        help="The one repository name sent with the goal. No default.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Provider model to ask (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Machine-readable JSON result on stdout",
    )
    parser.add_argument("goal", nargs="+", help="Goal to plan for")
    return parser


def request_input(repo: str, goal: str) -> str:
    """Everything about the operator's machine that this request carries.

    A name and a sentence. The earlier implementation this replaces sent the
    full configured repo list with every request, which described the operator's
    working set to a third party as a side effect of asking about one repo.
    """
    return json.dumps({"repo": repo, "goal": goal}, ensure_ascii=False)


def emit_failure(result: provider.ProviderResult, json_out: bool) -> int:
    """Report a failed request and choose its exit code.

    The five states stay apart in the message and in `--json`; the exit code is
    coarse by design. A reason with no mapping exits as a provider failure
    rather than as success — a state this command has not learned to name is
    not a plan.
    """
    reason = result.failure_reason or "unknown"
    detail = _FAILURE_TEXT.get(reason, "the request failed")
    print(
        f"ERROR: {result.provider} ({result.model}): {detail} [{reason}]",
        file=sys.stderr,
    )
    if json_out:
        print(json.dumps({
            "ok": False,
            "provider": result.provider,
            "model": result.model,
            "failure_reason": reason,
        }, indent=2, ensure_ascii=False))
    return _EXIT_FOR_FAILURE.get(reason, EXIT_PROVIDER)


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    repo = args.repo.strip()
    goal = " ".join(args.goal).strip()
    if not repo or not goal:
        print("ERROR: --repo and the goal must not be empty.", file=sys.stderr)
        return EXIT_INVOCATION

    try:
        selection = provider.select_provider(args.provider, args.model)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INVOCATION

    try:
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {PROMPT_PATH}: {exc}", file=sys.stderr)
        return EXIT_INVOCATION

    result = provider.run_request(
        selection,
        kind=REQUEST_KIND,
        instructions=instructions,
        input_text=request_input(repo, goal),
        schema=PLAN_SCHEMA,
        schema_name="mq_hal_plan",
    )

    if not result.ok or result.response is None:
        return emit_failure(result, args.json_out)

    plan: dict[str, Any] = result.response

    if args.json_out:
        print(json.dumps({
            "ok": True,
            "provider": result.provider,
            "model": result.model,
            "plan": plan,
        }, indent=2, ensure_ascii=False))
        return EXIT_OK

    # Rule 6: a result always says which provider produced it. A cloud plan and
    # a local one render the same way, so the line that tells them apart has to
    # be on the screen rather than inferred from which command was typed.
    print(f"Provider: {result.provider} ({result.model})")
    print()
    render(plan)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
