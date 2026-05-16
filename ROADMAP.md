# Roadmap

## Completed in v0.5.0

- HAL Timeline UI: compact terminal table view over local session memory.
- Timeline filters: repo, event type, limit, details.
- Output modes: table, details, JSON.
- README markdown rendering cleanup.

## Completed in v0.4.0

- HAL Session Memory: local JSONL history for doctor summaries, fix plans, and manual notes.
- Commands: `session`, `last`, `remember`, and `memory-path`.
- Automatic memory capture for `doctor-summary` and `fix-doctor`.
- Memory opt-out with `--no-memory` and `MQ_HAL_DISABLE_MEMORY=1`.
- Smoke test coverage for session memory.

## Completed in v0.3.0

- HAL Fix Planner: create safe copy-paste fix plans from HAL Doctor Summary.
- Planner command sanitization to block destructive suggestions.
- JSON and text output modes for fix plans.
- Smoke test coverage for fix planner.

## Completed in v0.2.0

- HAL Doctor Summary: run `mqlaunch doctor --json`, parse the result, and summarize health status.
- Deterministic fallback summary when Ollama is unavailable.
- Smoke test for doctor-summary output and JSON mode.

## v0.3 — Expanded intent set

- `open_editor` — open a file in $EDITOR
- `run_test` — run the test suite for the active repo
- `grep_repo` — search for a pattern in the repo
- `create_branch` — git checkout -b via natural language

## v0.4 — HAL Fix Planner

- `mq-hal fix-doctor` — read doctor summary, propose copy-paste fixes, run nothing automatically

## v0.5 — Multi-turn context

- Conversation history passed to Ollama across invocations
- Follow-up commands without repeating the repo name

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
