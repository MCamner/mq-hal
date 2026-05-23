# Roadmap

## v0.10.1 — Source readability + version sync

Status: done.

- [x] Fixed `docs/index.html` Pages version from v0.9.1 to v0.10.0
- [x] Added `tests/hal-router-smoke.sh` to CI workflow (was missing)
- [x] Added Proof section to README
- [x] Added `release-check.sh` — pre-release gate covering Python syntax, markdown guard, version sync, and all smoke tests
- [x] Extended `docs-smoke.sh` to verify `docs/index.html` version matches VERSION file

## v0.10.0 — HAL Stack Status

Status: done.

- [x] Added `mq-hal stack-status` — read-only local stack overview
- [x] Shows mq-hal, mqlaunch, repo-signal, optional bridget, configured repos, git state, VERSION, and repo-signal publish status
- [x] Added `tests/stack-status-smoke.sh`
- [x] Documented Stack Status in README and command surface docs

## v0.9.x — HAL Audit + Release Brief + Repo Ops + Session + Timeline

Status: done.

- [x] `mq-hal audit` — publish quality and README score via repo-signal
- [x] `mq-hal release-brief` — release readiness check
- [x] `mq-hal repo-status` — read-only git status
- [x] `mq-hal ci` — GitHub Actions status
- [x] `mq-hal doctor-summary` + `mq-hal fix-doctor`
- [x] `mq-hal session` / `last` / `remember` / `timeline`
- [x] `mq-hal stack-status`
- [x] README markdown guard (`tools/markdown_guard.py`)
- [x] 13 smoke test suites covering all commands

## v0.6 — Notifications

- Desktop notification (macOS `osascript`) on long-running command completion

## v1.0 — Stable API

- Locked intent schema with version field
- Plugin system for custom intent handlers
- Homebrew formula

## Ideas / Backlog

- Web UI (local) for command history
- Multiple model backends (LM Studio, llama.cpp)
- Team-shared repo config via URL
