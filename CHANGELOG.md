# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to mq-hal are documented here.

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
