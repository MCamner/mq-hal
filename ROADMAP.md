# Roadmap

## v0.2 — Multi-turn context
- Conversation history passed to Ollama across invocations
- Follow-up commands without repeating the repo name

## v0.3 — Expanded intent set
- `open_editor` — open a file in $EDITOR
- `run_test` — run the test suite for the active repo
- `grep_repo` — search for a pattern in the repo
- `create_branch` — git checkout -b via natural language

## v0.4 — Notifications
- Desktop notification (macOS `osascript`) on long-running command completion

## v1.0 — Stable API
- Locked intent schema with version field
- Plugin system for custom intent handlers
- Homebrew formula

## Ideas / Backlog
- Web UI (local) for command history
- Multiple model backends (LM Studio, llama.cpp)
- Team-shared repo config via URL
