# Cloud Provider Boundary

`mq-hal` is a local-first operator layer. This document fixes the terms under
which any part of it may talk to an external model provider.

It is written before the implementation exists. Today `mq-hal` makes no
external provider request at all: every model call goes to a local Ollama
endpoint. The contract below governs the work that adds one.

Two rules carry the rest:

> **Network egress is a command-surface decision, not a model-profile side
> effect.**
>
> **A failed provider never silently becomes another provider.**

## Why this exists

An earlier implementation of cloud planning was built on the branch
`mq/update-shell-scripts-20260824-001140` and never merged. It is kept as
reference material. Reading it produced this contract, because it demonstrated
the failure modes concretely rather than hypothetically:

- It moved the trust boundary into configuration. Flipping `provider` in
  `config/models.json` from `ollama` to `openai` made `mq-hal plan` and
  `mq-hal critic` — commands with an established local meaning — send data to
  an external service. Same command, same flags, different trust boundary.
- It offered no way to say yes. The only control was `--no-ai`, an opt-out.
- It collapsed every failure into one value. A missing credential, a DNS
  failure, a timeout, an HTTP error and unparseable output all returned
  `None`, and the caller turned that into a local stub result with a warning.
  A mistyped key was indistinguishable from an offline laptop, and both were
  indistinguishable from a normal local answer.

The transport itself was sound — no credential in argv, `store: false`,
strict JSON-schema responses — and that part is worth re-deriving. The
boundary around it was not.

## The contract

### 1. Local commands stay local

Existing local-first commands, `mq-hal plan` and `mq-hal critic` among them,
must not become cloud-backed through model-profile configuration. Their normal
execution path performs no external network request.

This is structural, not a property of today's `config/models.json`. A local
command must be unable to select a cloud provider through configuration alone,
so that editing a JSON file cannot move the trust boundary. Cloud gets its own
command surface.

### 2. Cloud requires explicit operator intent

A cloud request may occur only from a command or option whose documented
command surface names cloud execution.

Changing configuration is not consent to data egress.

### 3. Egress is observable before transfer

Every outbound provider request writes one metadata-only line to stderr
**before** network I/O begins:

```text
cloud egress: provider=openai model=gpt-... kind=code-plan bytes=18432
```

The line identifies at least the provider, the model, the request kind and the
payload byte count. It carries no credential, no prompt text, no file content
and no path.

One line per request, not one per process. A single command run may make
several provider calls with different models, payloads and sizes; a line
emitted once would tell the truth about the first and conceal the rest.

### 4. Credentials are process inputs

`OPENAI_API_KEY` is read only from the process environment. `mq-hal` does not
read the macOS Keychain itself — the existing stack boundary already covers
that:

```text
Keychain → trusted launcher/process → OPENAI_API_KEY → mq-hal
```

A credential must never appear in argv, stdout, stderr, logs, generated plans,
or persisted request metadata.

One place already reads it: `scripts/stack_status.py` tests whether
`OPENAI_API_KEY` is set to decide between reporting `configured` and `unknown`.
It emits the verdict, never the value. That is the pattern — a credential may
be observed, never reproduced.

### 5. Failure states remain distinct

At minimum these five, and they must not collapse into one null result:

| State | Meaning |
| --- | --- |
| `credential-missing` | cloud was requested and no credential is available |
| `transport-unavailable` | DNS, socket, connection or timeout failure |
| `provider-http-error` | the provider answered with an HTTP error |
| `response-invalid` | the answer could not be parsed |
| `schema-invalid` | valid JSON that violates the requested schema |

Two of them differ in whether anything left the machine, and the egress notice
is what records the difference:

```text
credential-missing      fail before network I/O   → no egress line
transport-unavailable   the attempt was made      → egress line already written
```

### 6. No implicit provider fallback

```text
local failure   ≠ permission to call cloud
cloud failure   ≠ permission to return a local result as though the cloud
                  operation had succeeded
```

Any fallback between providers requires explicit operator intent and stays
visible in the result. A result must always say which provider produced it.

### 7. Machine output stays machine-clean

Egress notices and operational diagnostics go to stderr. Structured `--json`
output goes to stdout only.

### 8. Provider transport does not choose policy

Provider selection happens before the transport client is called. The OpenAI
client executes an already-selected request; it does not decide when OpenAI
should be used.

```text
task/request → provider selection → selected provider → provider client → result
```

## Exit codes

Five failure states do not become five exit codes. Shell policy stays coarse
and machine semantics stay precise:

| Code | Meaning |
| --- | --- |
| 0 | operation succeeded |
| 2 | invocation or configuration error |
| 3 | credential unavailable |
| 4 | provider operation failed |

The precise state belongs in the machine-readable result, not in the exit
code.

## What this document does not decide

It does not name the cloud-facing commands, their flags, their payloads or
their output shape. Those belong to the command surface that introduces them,
and to `docs/COMMAND_SURFACE.md`.
