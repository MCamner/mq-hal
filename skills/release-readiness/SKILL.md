---
name: release-readiness
description: Use when preparing mq-hal for release by checking versioning, changelog, docs, smoke tests, prompts, command surface, and integration readiness.
---

# Release Readiness

Use this skill before tagging, publishing, or announcing mq-hal.

## Always Inspect

- `git status --short`
- `VERSION`
- `README.md`
- `CHANGELOG.md`
- `docs/index.html`
- `docs/hal-command-surface.md`
- `docs/INTEGRATION.md`
- `bin/mq-hal`
- `scripts/*.py`
- `tests/*-smoke.sh`
- `release-check.sh`

## Blockers

- version mismatch across `VERSION`, README badge, changelog, and `docs/index.html`
- failing `release-check.sh`
- changed command routing without docs or smoke tests
- prompt/schema drift between `prompts/system.txt` and `scripts/hal.py`
- unsafe new subprocess behavior
- undocumented integration dependency
- dirty worktree containing unrelated user changes

## Verification

```bash
./release-check.sh
```

If a narrower check is enough:

```bash
python3 -m py_compile scripts/hal.py scripts/*.py tools/*.py
./tests/smoke.sh
./tests/hal-router-smoke.sh
./tests/docs-smoke.sh
```

## Report Format

Return:

- status: ready, blocked, or uncertain
- blockers
- files changed
- checks run
- checks skipped and why
- next concrete action
