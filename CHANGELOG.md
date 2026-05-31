# Changelog

<!-- markdownlint-disable MD013 -->

## [1.0.1] - 2026-05-31

### Added

- `mq-hal learn` — local lesson store for verified learnings from Codex,
  Claude, or manual work. Subcommands: `add`, `list`, `show <id>`,
  `search <query>`, `summarize`. Storage: `~/.mq-hal/learn/lessons.jsonl`.
- Secret redaction before write: `api_key:`, `token:`, `bearer`, `ghp_*`,
  `sk-*` patterns are replaced with `[REDACTED]`.
- `docs/LEARNING.md` — learn layer documentation with storage format,
  safety rules, and distinction from session memory.
- `tests/learn-smoke.sh` — 8-step smoke test covering add, list, show,
  search, summarize, redaction, and JSON output. Wired into CI and
  `release-check.sh`.

### Changed

- `docs/COMMAND_SURFACE.md` — `learn` added to named command table
  (34 commands total, Memory=Yes).
- `release-check.sh` — `learn.py` syntax check and `learn-smoke.sh`
  added to smoke test suite.

## [1.0.0] - 2026-05-31

### Added

- `docs/FORMATS.md` — declares stable on-disk formats for repo config
  (`config/repos.json`), session memory (`~/.mq-hal/session.jsonl`) and
  timeline output.
- `docs/TROUBLESHOOTING.md` — common problems and fixes for install, config,
  Ollama, model profiles, release-check, smoke tests and session memory.

### Changed

- ROADMAP v1.0.0 requirements fully satisfied: all 19 items done.
- Release map updated: v0.15.x marked done, v1.0.0 promoted to current.
- README version badge updated to blue (stable release).
- GitHub Pages subtitle updated to "stable local HAL command router".

### Security

- Full safety audit: no `shell=True`, no `os.system`, intent output
  normalized before routing, path escape protection (`is_within()`),
  executor `validate_command` + critic gate + dry-run default. No
  critical safety gaps found.

## [0.15.2] - 2026-05-31

### Changed

- `release-check.sh` now checks whether the GitHub release tag for the current
  version already exists; fails if it does, preventing accidental re-release.
- `release-check.sh` smoke tests use `|| fail "..."` so all failures are
  collected and reported together with the FAILED banner, instead of exiting
  silently at the first failure.
- `tools/check-command-docs.sh` extracts commands dynamically from the case
  statement in `bin/mq-hal` instead of a hardcoded list, blocking release if
  any dispatched command is undocumented in `docs/COMMAND_SURFACE.md`.
- ROADMAP release gate v2 items marked complete.

## [0.15.1] - 2026-05-31

### Fixed

- `tests/repo-memory-smoke.sh` now points repo-memory at the active checkout
  via `MQ_HAL_CONFIG_PATH`, so GitHub Actions does not depend on `~/mq-hal`
  existing on the runner.
- `scripts/repo_memory.py` supports `MQ_HAL_CONFIG_PATH` for deterministic
  test and CI configuration overrides.

## [0.15.0] - 2026-05-31

### Added

- Visual HAL: `mq-hal analyze-diagram`, `mq-hal review-ui`, and
  `mq-hal architecture-brief` for read-only diagram/UI observations,
  trust-boundary prompts, and draft YAML output.
- `scripts/visual_hal.py` with deterministic local fallback and optional
  read-only `mq-image-analyze` context when available.
- Install/update flow: `install.sh`, `uninstall.sh`, `upgrade.sh`,
  `mq-hal version`, `mq-hal config-check`, and `mq-hal update`.
- `docs/INSTALL.md` with PATH setup, shell completion notes, clean reinstall
  steps, uninstall behavior, and an optional Homebrew formula plan.
- `release-check.sh --dry-run` for non-mutating release validation.
- `tests/visual-hal-smoke.sh` and `tests/install-flow-smoke.sh`, wired into
  CI, `tests/smoke.sh`, and `release-check.sh`.

### Changed

- Command registry, command surface docs, README proof list, and roadmap now
  include Visual HAL and install/update commands.

## [0.14.2] - 2026-05-31

### Added

- `scripts/executor.py` — `mq-hal execute plan.json --confirm`: executes a
  validated plan step by step after a pre-flight critic check. Without
  `--confirm`, it prints a dry-run preview.
- `execute` refuses critic `FAIL` plans, rejects shell operators in
  `safe_command`, and asks again for steps marked `requires_confirm`.
- `tests/execute-smoke.sh` — 5 checks covering dry-run preview, confirmed
  safe execution, dangerous-plan refusal, and shell-operator refusal.
- `scripts/model_profiles.py` plus `--model <profile>` for the router and
  planner, backed by `config/models.json`.
- `scripts/model_status.py` — `mq-hal model-status`: read-only Ollama
  reachability, latency, and configured profile availability check.
- `scripts/model_test.py` — `mq-hal model-test`: read-only structured
  generation smoke check for a selected model profile.
- Prompt regression smoke tests for deterministic routing.
- `scripts/repo_memory.py` — `mq-hal index/search/ask-repo/repo-map`:
  local deterministic repo memory with optional Ollama embeddings.
- `scripts/critic.py` — `mq-hal critic plan.json`: deterministic safety
  review of a saved plan with 8 checks: rollback, validation, confirmation
  flags, dangerous commands, known repos, scope (file count), step count,
  and missing tests. Verdict: PASS / REVIEW / FAIL.
- Reads from file path, stdin (`-`), or `--sample`. Returns exit 1 on FAIL.
- `tests/critic-smoke.sh` — 6 checks including dangerous plan → FAIL and
  clean plan → PASS/REVIEW assertions.

## [0.14.1] - 2026-05-30

### Added

- `scripts/planner.py` — `mq-hal plan "<goal>"`: generates a structured
  local plan via Ollama with goal, affected repos/files, risk level,
  numbered steps with safe_command and requires_confirm, validation
  checklist, and rollback_plan.
- `prompts/planner.txt` — dedicated planning system prompt with risk
  level definitions and safety rules.
- `--out <file>` flag saves the plan to a JSON file for use with
  `mq-hal critic` (future).
- `--no-ai` returns a stub plan; Ollama fallback on unavailability.
- `tests/plan-smoke.sh` — 6 checks: syntax, sample output, section
  headings, JSON shape, --out file save, --no-ai stub plan.

## [0.14.0] - 2026-05-30

### Added

- `config/tools.json` — machine-readable tool registry: 16 named
  commands with risk_level, requires_confirm, uses_ai, writes_memory,
  and mqlaunch_alias.
- `scripts/tools_list.py` — `mq-hal tools` and `mq-hal tools --json`:
  list available HAL tools from the registry.
- `config/models.json` — model profile registry: router, planner,
  critic, code profiles with model name and reasoning_effort.
- `scripts/models_list.py` — `mq-hal models` and `mq-hal models --json`:
  show available model profiles.
- Intent schema carry-forward (from v0.11.0): `risk_level`,
  `rollback_plan`, `requires_confirmation` added as optional nullable
  fields to `schemas/intent.schema.json` and `INTENT_SCHEMA` in
  `hal.py`. `parse_intent` and `empty_intent` updated accordingly.
- Session summaries: `mq-hal session` now shows a type-count summary
  at the bottom of the event list.
- `tests/tools-smoke.sh` and `tests/models-smoke.sh` (4 checks each).
- All new smoke tests wired into `tests/smoke.sh`, `release-check.sh`,
  and `.github/workflows/tests.yml`.

### Fixed

- `handle_intent` in `hal.py`: move `refuse` and mqlaunch allowlist
  rejection before `resolve_repo`/`ensure_repo_exists` — fixes CI
  failure on GitHub Actions where configured repos do not exist on the
  runner.
- `tests/router-safety-smoke.sh`: replace CLI-level `--confirm` test
  (which needed a real repo path) with a Python-level test using
  `confirm_command` and `run_planned_command` directly.

## [0.13.0] - 2026-05-30

### Added

- `scripts/hello.py` — `mq-hal hello` / `mq-hal status-screen`: greeting
  and quick status screen showing active repo, version, memory brief, and
  recent session events.
- `timeline --compact` flag: short format showing only time, type, and
  repo — no status column, useful for at-a-glance overviews.
- `docs/BRIDGET.md` — Bridget/HAL identity doc: roles, architecture,
  design rules, and identity background.
- `docs/VOICE_MODE.md` — voice mode design doc: principles, non-goals,
  proposed local TTS/STT pipeline, Bridget voice toggle design, and
  safety constraints.
- `tests/hello-smoke.sh` — 5-check smoke test covering syntax, sample
  output, section headings, JSON shape, and status-screen alias.
- `hello` added to `docs/COMMAND_SURFACE.md` and
  `tools/check-command-docs.sh`.
- Both new tests wired into `tests/smoke.sh` and `release-check.sh`.

## [0.12.0] - 2026-05-29

### Added

- `scripts/memory_status.py` — `mq-hal memory-status` and
  `mq-hal memory-brief`: show mq-agent semantic memory state with graceful
  fallback if mq-agent is not installed. Checks `$MQ_AGENT_BIN`, PATH,
  and known local paths.
- `scripts/agent_brief.py` — `mq-hal agent-brief`: mq-agent availability
  and memory summary in one command.
- mq-agent added to `mq-hal stack-status` tools table.
- Memory brief line added to `mq-hal brief` and `mq-hal release-brief`
  output.
- `tests/memory-status-smoke.sh` and `tests/agent-brief-smoke.sh` —
  smoke tests covering sample output, JSON shape, brief format, and
  fallback when mq-agent is absent.
- Both new smoke tests wired into `tests/smoke.sh` and `release-check.sh`.
- `memory-status`, `memory-brief`, and `agent-brief` added to
  `docs/COMMAND_SURFACE.md` and `tools/check-command-docs.sh`.

## [0.11.0] - 2026-05-29

### Added

- `schemas/intent.schema.json` — formal JSON Schema for the mq-hal intent
  contract, extracted from the inline dict in `scripts/hal.py`.
- `docs/INTENT_CONTRACT.md` — complete contract covering all 15 intent
  types, field reference, rejection behavior table, no-AI deterministic
  fallback patterns, and valid/rejected examples.
- `docs/COMMAND_SURFACE.md` — compact canonical command registry: 13
  named commands with AI/memory/confirm flags and mqlaunch aliases, plus
  the full router intent allowlist with safety classes.
- `tests/intent-schema-smoke.sh` — 7-check smoke test verifying schema
  file integrity, schema/code enum parity, unknown intent → refuse,
  malformed JSON → refuse, path escape rejection, and branch name
  validation.
- `tests/router-safety-smoke.sh` — 6-check smoke test verifying handler
  coverage via AST analysis, refuse exit 2, unknown mqlaunch exit 2,
  `--confirm` cancel exit 130, empty prompt help, and mqlaunch allowlist
  structure.
- `tools/check-command-docs.sh` — fails if any canonical command is
  missing from `docs/COMMAND_SURFACE.md` or `bin/mq-hal` dispatch.
- Intent contract verification step in `release-check.sh`: checks file
  presence and validates schema const and enum match `hal.py` at release
  time.
- Intent contract smoke tests and command surface check added to
  `tests/smoke.sh` and `release-check.sh`.

## [0.10.1] - 2026-05-23

### Fixed

- Fixed `docs/index.html` Pages version badge from v0.9.1 to v0.10.1 (was two releases behind).
- Added `tests/hal-router-smoke.sh` to CI workflow — it existed but was never run in CI.

### Added

- `release-check.sh` — pre-release gate covering Python syntax check for all scripts, README markdown guard, version sync across README/CHANGELOG/docs/index.html, and all 13 smoke tests.
- `Proof` section in README listing what is verified: JSON-only model output, router allowlist enforcement, fix planner no-execute guarantee, local session memory, and smoke test coverage.
- `docs-smoke.sh` now checks that `docs/index.html` version matches `VERSION` file.
- `tools/markdown_guard.py` now requires `## Proof` section in README.

## [0.10.0] - 2026-05-20

### Added

- Added `mq-hal stack-status` for a read-only local stack overview.
- Shows `mq-hal`, `mqlaunch`, `repo-signal`, optional `bridget`, configured repos, git state, VERSION, and repo-signal publish status.
- Added `tests/stack-status-smoke.sh`.
- Documented Stack Status in README and command surface docs.

## [0.9.2] - 2026-05-19

### Fixed

- Added `tools/write_readme.py` to regenerate README with clean fenced code blocks.
- Added `tools/markdown_guard.py` to prevent flattened README rendering regressions.
- Strengthened docs smoke coverage to run the README markdown guard.
- Regenerated README for the v0.9.x HAL command surface.

<!-- markdownlint-disable MD024 -->

## [0.9.1] - 2026-05-17

### Fixed

- Fixed `release-brief` opening ChatGPT browser tabs when called via `mq-hal`. The `run()` helper in `release_brief.py` now passes `stdin=subprocess.DEVNULL` so subprocesses cannot block on terminal input or trigger `pause_enter` reads.
- Synced `docs/index.html` version badge from v0.9.0 to v0.9.1.
- Strengthened `docs-smoke.sh` from 12 to 15 checks: command surface file existence, README links to command surface, and clean fence info string validation.

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
