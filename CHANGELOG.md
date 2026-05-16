# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to mq-hal are documented here.

## [0.5.1] – 2026-05-16

### Added

- Added `docs/INTEGRATION.md` — HAL Integration Contract covering architecture, feature contract, bridge contract, tool policy, safety rules, memory policy, and versioning strategy.
- Added `tests/docs-smoke.sh` — verifies README, integration contract, and key structural markers.
- Added docs smoke test to CI.

### Fixed

- Rewrote README with consistent `---` separators so GitHub renders all code blocks correctly.

## [0.5.0] – 2026-05-16

### Added

- Added `mq-hal timeline` — compact terminal table view over HAL Session Memory.
- Added `--details` flag to show one-line summary under each timeline row.
- Added `--repo`, `--type`, `--limit`, and `--json` filters for timeline.
- Added `tests/timeline-smoke.sh` and CI coverage for `timeline.py`.

### Fixed

- Rewrote README markdown for clean GitHub rendering — each code block separated by blank lines.

## [0.4.0] – 2026-05-16

### Added

- Added HAL Session Memory backed by local JSONL storage in `~/.mq-hal/session.jsonl`.
- Added `mq-hal session`, `mq-hal last`, `mq-hal remember`, and `mq-hal memory-path` commands.
- Added automatic memory capture for `doctor-summary` and `fix-doctor` results.
- Added `--no-memory` flag to `doctor-summary` and `fix-doctor` to suppress memory writes.
- Added `MQ_HAL_DISABLE_MEMORY=1` environment variable to disable memory globally.
- Added `tests/session-memory-smoke.sh` and CI coverage for `session_memory.py`.
- Fixed double-save: `fix-doctor` subprocess call to `doctor_summary.py` now uses `--no-memory`.

## [0.3.1] – 2026-05-16

### Fixed

- Fixed CI failure in `fix-planner-smoke.sh` — added `--sample` flag to `fix_planner.py` so smoke tests run against embedded sample data instead of requiring a live `macos-scripts` repo on the runner.

## [0.3.0] – 2026-05-16

### Added

- Added `mq-hal fix-doctor` for safe fix planning from HAL Doctor Summary.
- Added command sanitization — blocks destructive tokens, allowlist-filters suggestions.
- Added `prompts/fix-planner.txt` system prompt for the planner model.
- Added `tests/fix-planner-smoke.sh` with syntax, JSON, and text output checks.
- Updated CI to cover `fix_planner.py` syntax and fix-planner smoke test.

## [0.2.0] – 2026-05-16

### Added

- Added `mq-hal doctor-summary` — runs `mqlaunch doctor --json`, parses the output, and summarizes health status with Ollama.
- Added deterministic fallback summary when Ollama is unavailable (`--no-ai`).
- Added `--json` output mode for machine-readable summary.
- Added `--sample` flag for smoke testing without a live repo.
- Added `prompts/doctor-summary.txt` system prompt for the summary model.
- Added `tests/doctor-summary-smoke.sh` with syntax, text, and JSON checks.
- Updated CI to cover `doctor_summary.py` syntax and smoke test.

## [0.1.0] – 2026-05-16

### Added

- Natural language command routing via Ollama (qwen3:4b-instruct)
- Structured JSON intent schema with allowlist enforcement
- Safe intent set: `help`, `list_repos`, `switch_repo`, `print_cd`, `pwd`, `repo_tree`, `git_status`, `git_log`, `run_mqlaunch`, `refuse`
- `mqlaunch` command allowlist: `doctor`, `release-check`, `selftest`, `perf`, `system-check`, `demo`
- Persistent active-repo state in `~/.mq-hal/state.json`
- `--cd` flag for shell `cd` integration (`mqhcd` zsh helper)
- `--list-repos` flag
- `--raw-intent` flag for debugging model output
- `OLLAMA_URL` and `OLLAMA_MODEL` environment variable overrides
- Symlink-safe bin wrapper via `python3 os.path.realpath`
