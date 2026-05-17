# Changelog

<!-- markdownlint-disable MD024 -->

## [0.9.1] - 2026-05-17

### Fixed

- Fixed `release-brief` opening ChatGPT browser tabs when called via `mq-hal`. The `run()` helper in `release_brief.py` now passes `stdin=subprocess.DEVNULL` so subprocesses cannot block on terminal input or trigger `pause_enter` reads.

## [0.9.0] - 2026-05-17

### Added

- Added `mq-hal audit` — publish quality and README quality audit via `repo-signal`.
- Runs `repo-signal publish-checklist` and `repo-signal readme-score`, derives overall status (`ready` / `needs_review` / `not_ready`).
- Supports `--json`, `--sample`, `--repo`, `--no-memory`.
- Added `tests/audit-smoke.sh` (4 checks).
- Extended `docs-smoke.sh` to 12 checks including Audit coverage.
- Documented HAL Audit in README.

## [0.8.1] - 2026-05-17

### Fixed

- Stabilized GitHub Actions workflow for the v0.8.x command set.
- Added `--sample` flag to `brief.py` so smoke tests run without requiring a live repo.
- Hardened `release-brief-smoke.sh` to 5 checks including `release` alias routing.
- Strengthened `docs-smoke.sh` to 11 checks including Release Brief coverage.

## [0.8.0] - 2026-05-17

### Added

- Added `mq-hal release-brief` for read-only release readiness summaries.
- Checks VERSION, CHANGELOG, README version reference, git state, CI status, latest release, doctor summary, and release-check.
- Supports `--json`, `--sample`, `--skip-gh`, `--skip-doctor`, `--skip-release-check`, `--no-memory`.
- Added `tests/release-brief-smoke.sh` and CI workflow coverage.
- Added `brief-smoke.sh` to CI workflow (was missing).

## [0.7.1] - 2026-05-17

### Fixed

- Regenerated README with balanced fenced code blocks for clean GitHub rendering.
- Added HAL Repo Ops section to README documenting `repo-status` and `ci`.
- Strengthened docs smoke test to 10 checks including Repo Ops coverage.
- Synced GitHub Pages with v0.7.1 command set.

## [0.7.0] - 2026-05-17

### Added

- Added `mq-hal repo-status` — read-only git repo status with branch, dirty state, recent commits, and tags.
- Added `mq-hal ci` — read-only GitHub Actions status via `gh run list`.
- Both commands support `--json`, `--sample`, and `--repo` flags.
- Added `tests/repo-status-smoke.sh` and `tests/ci-status-smoke.sh`.
- Added CI syntax and smoke coverage for both new scripts.

## [0.6.0] - 2026-05-17

### Added

- Added `mq-hal brief` — quick status snapshot combining git, doctor, CI, release, and last session note.
- Added `mqlaunch hal brief` bridge command.
- Updated HAL menu with Observe / Plan / Memory / Debug sections; Brief is now item 1.
- Added `tests/brief-smoke.sh`.

## [0.5.2] - 2026-05-17

### Fixed

- Rewrote README using generated fenced code blocks to fix GitHub rendering.
- Strengthened docs smoke test to check balanced markdown fences and multiline helper examples.

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
