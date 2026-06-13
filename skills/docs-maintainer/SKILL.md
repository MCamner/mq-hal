---
name: docs-maintainer
description: Use when keeping mq-hal README, command surface docs, integration docs, GitHub Pages, changelog, roadmap, or prompt documentation consistent with code.
---

# Docs Maintainer

Keep mq-hal docs aligned with the actual command router and smoke-tested behavior.

## Evals

### Should trigger

- "sync the README after a command surface change"
- "the command surface docs are stale"
- "update the changelog and roadmap"
- "do documented intents still match the router?"

### Should not trigger

- "change intent routing or safety" → use `hal-router-safety-maintainer`
- "polish the CLI output" → use `terminal-ui-polisher`
- "is mq-hal ready to release?" → use `release-readiness`

## Docs Surfaces

- `README.md`
- `docs/hal-command-surface.md`
- `docs/INTEGRATION.md`
- `docs/index.html`
- `CHANGELOG.md`
- `ROADMAP.md`
- `prompts/system.txt`

## Verify Claims Against Code

For command claims, check:

- `bin/mq-hal`
- `scripts/hal.py`
- `scripts/*.py`
- `tests/*-smoke.sh`

For integration claims, check:

- `config/repos.json`
- `scripts/stack_status.py`
- `scripts/audit.py`
- `scripts/release_brief.py`
- `scripts/ci_status.py`

## Common Drift

- README command list misses wrapper aliases.
- Prompt examples mention intents not in `ALLOWED_INTENTS`.
- Docs imply writes when command only plans.
- Version badge, `VERSION`, changelog, and `docs/index.html` disagree.
- Integration docs assume optional dependencies are always available.

## Verification

```bash
./tests/docs-smoke.sh
python3 tools/markdown_guard.py README.md
./tests/smoke.sh
```

For release-facing docs:

```bash
./release-check.sh
```

## Editing Guidance

Document only behavior that exists or is added in the same change. Keep safety language explicit: model proposes JSON intent, router enforces allowlist.
