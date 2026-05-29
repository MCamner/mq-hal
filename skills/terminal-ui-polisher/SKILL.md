---
name: terminal-ui-polisher
description: Use when improving mq-hal CLI output, help text, reports, JSON modes, smoke output, error messages, or mqlaunch HAL menu integration.
---

# Terminal UI Polisher

Use this skill to make mq-hal command output clear, compact, scriptable, and safe.

## Surfaces

- `bin/mq-hal`
- `scripts/hal.py`
- `scripts/brief.py`
- `scripts/release_brief.py`
- `scripts/audit.py`
- `scripts/stack_status.py`
- `scripts/doctor_summary.py`
- `scripts/fix_planner.py`
- `scripts/session_memory.py`
- `scripts/timeline.py`
- `docs/hal-command-surface.md`

## Principles

- Keep human output concise and action-oriented.
- Keep `--json` output stable and machine-readable.
- Clearly distinguish read-only reports from plans or confirmed actions.
- Show missing optional dependencies as warnings, not crashes, when possible.
- Avoid decorative output that hides repo, status, or next step.
- Preserve direct command use from mqlaunch and mq-mcp.

## Review Checklist

- Help output lists the real commands and aliases.
- Errors include the command or repo that failed.
- Fallback behavior is visible when Ollama, GitHub CLI, repo-signal, or mqlaunch is unavailable.
- Report output names the target repo.
- JSON modes do not include ANSI color.
- Smoke tests cover important output markers.

## Verification

```bash
./tests/brief-smoke.sh
./tests/release-brief-smoke.sh
./tests/audit-smoke.sh
./tests/stack-status-smoke.sh
./tests/doctor-summary-smoke.sh
./tests/timeline-smoke.sh
./tests/session-memory-smoke.sh
```

## Output Standard

When editing CLI UX, keep the style consistent across scripts and add smoke checks for any new headline, status, or JSON field that callers rely on.
