---
name: hal-router-safety-maintainer
description: Use when adding, changing, reviewing, or documenting mq-hal intents, routing, prompts, subprocess calls, repo allowlists, confirmations, or safety behavior.
---

# HAL Router Safety Maintainer

Use this skill for mq-hal's core safety boundary: natural language can suggest an intent, but only local allowlisted router code can act.

## Evals

### Should trigger

- "add a new HAL intent"
- "review the repo allowlist for a subprocess call"
- "does this intent need a confirmation gate?"
- "tighten routing safety boundaries"

### Should not trigger

- "polish the HAL menu output" → use `terminal-ui-polisher`
- "update intent docs only" → use `docs-maintainer`
- "add a runtime health check" → use `runtime-observability-maintainer`

## Core Files

- `scripts/hal.py`
- `prompts/system.txt`
- `config/repos.json`
- `bin/mq-hal`
- `tests/hal-router-smoke.sh`
- `tests/smoke.sh`
- `docs/hal-command-surface.md`
- `README.md`

## Safety Contract

- The model must output schema `mq-hal.intent.v1`.
- Intent names must be in `ALLOWED_INTENTS`.
- mqlaunch commands must be in `ALLOWED_MQLAUNCH`.
- Repo names must resolve through `config/repos.json`.
- Shell commands must not be constructed from raw model text.
- Risky or write-like actions need explicit user confirmation.
- Read-only report commands should stay read-only.

## Adding An Intent

When adding or changing an intent:

1. Add the intent to `ALLOWED_INTENTS`.
2. Update `INTENT_SCHEMA`.
3. Add deterministic fallback handling if appropriate.
4. Route to a narrow function with explicit arguments.
5. Add smoke coverage.
6. Update `prompts/system.txt` examples and constraints.
7. Update README and `docs/hal-command-surface.md`.

## Risk Review

Check for:

- `subprocess.run(..., shell=True)`
- unbounded command args
- raw user prompt passed to shell
- repo path traversal or unregistered repos
- accidental writes to repo files
- GitHub or network calls without graceful fallback
- state writes outside `MQ_HAL_STATE_DIR`

## Verification

```bash
python3 -m py_compile scripts/hal.py
./tests/hal-router-smoke.sh
./tests/smoke.sh
./tests/docs-smoke.sh
```

For full confidence:

```bash
./release-check.sh
```

## Review Standard

Lead with safety regressions, missing smoke tests, prompt/schema drift, and unbounded subprocess behavior. Treat docs drift as a safety bug because users rely on the documented command surface.
