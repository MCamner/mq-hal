---
name: integration-stack-maintainer
description: Use when working on mq-hal integration with mqlaunch, repo-signal, mq-mcp, configured repos, stack status, CI status, or release/report workflows.
---

# Integration Stack Maintainer

Use this skill when mq-hal connects to the wider MQ ecosystem.

## Integration Role

`mq-hal` is the local operator/router layer. It sits between natural-language requests and safe local repo/tool actions.

Important integrations:

- `mqlaunch` for doctor, release-check, selftest, perf, system check, and demo commands
- `repo-signal` for audit and publish-readiness signals
- GitHub CLI for CI and release status when available
- `mq-mcp` as a tool surface that can call mq-hal read-only reports
- `config/repos.json` as the repo registry

## Files To Inspect

- `scripts/stack_status.py`
- `scripts/audit.py`
- `scripts/brief.py`
- `scripts/release_brief.py`
- `scripts/repo_status.py`
- `scripts/ci_status.py`
- `scripts/doctor_summary.py`
- `scripts/fix_planner.py`
- `docs/INTEGRATION.md`
- `README.md`
- `tests/*-smoke.sh`

## Change Rules

- Keep integration commands read-only unless the user explicitly asks for a planning or confirmed action.
- Every optional dependency should fail gracefully with a clear message.
- Prefer JSON modes for machine-readable integration points.
- Keep configured repos explicit; do not scan broad home paths by default.
- Do not assume `gh`, `repo-signal`, `mqlaunch`, or Ollama are installed unless checked.

## Verification

```bash
./tests/stack-status-smoke.sh
./tests/audit-smoke.sh
./tests/brief-smoke.sh
./tests/release-brief-smoke.sh
./tests/repo-status-smoke.sh
./tests/ci-status-smoke.sh
./tests/doctor-summary-smoke.sh
```

Run `./release-check.sh` before release or after broad integration changes.

## Output Standard

For integration work, report which dependencies were present, which paths were configured, what was verified, and what gracefully degraded.
