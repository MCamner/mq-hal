---
name: runtime-observability-maintainer
description: Use when adding or changing mq-hal runtime health, stack status, vector health, model health, tool availability, diagnostics, environment reports, or degraded-mode recommendations.
---

# Runtime Observability Maintainer

Use this skill when mq-hal summarizes the health of the local mq ecosystem.

## Evals

### Should trigger

- "add a vector health check"
- "the model health summary is wrong"
- "improve degraded-mode recommendations"
- "the stack status diagnostics are stale"

### Should not trigger

- "change intent routing" → use `hal-router-safety-maintainer`
- "wire a new external integration" → use `integration-stack-maintainer`
- "polish the report layout" → use `terminal-ui-polisher`

## Boundary

mq-hal owns operator-facing diagnostics, runtime summaries, local model status, tool availability, environment state and degraded-mode recommendations.

It must not own cognition, review generation, semantic memory indexing, or direct shell execution from model output.

## Files To Inspect

- `scripts/stack_status.py`
- `scripts/doctor_summary.py`
- `scripts/brief.py`
- `scripts/release_brief.py`
- `scripts/hal.py`
- `docs/INTEGRATION.md`
- command-surface docs
- `tests/*smoke.sh`

## Safety Rules

- Redact secrets and tokens.
- Treat optional tools as degraded states, not crashes.
- Keep health commands read-only.
- Do not execute fixes automatically.
- Keep JSON summaries stable for mq-agent and mqlaunch consumers.

## Verification

```bash
./tests/stack-status-smoke.sh
./tests/doctor-summary-smoke.sh
./tests/docs-smoke.sh
./release-check.sh
```

Report which dependencies were present, missing, or degraded.
