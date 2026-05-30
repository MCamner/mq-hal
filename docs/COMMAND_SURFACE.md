# Command Surface

Canonical registry of all named `mq-hal` commands.

Every command listed here must have:

- a case entry in `bin/mq-hal`
- a smoke test
- documentation in `docs/hal-command-surface.md`

The detailed reference with flags, examples, and backend notes is in
`docs/hal-command-surface.md`.

---

## Named commands

| Command | Aliases | AI | Memory | Confirm | mqlaunch |
| --------------- | --------------------------------- | --- | ------ | ------- | -------------------- |
| `brief` | — | Yes | Yes | No | `hal brief` |
| `audit` | — | Yes | Yes | No | `hal audit` |
| `stack-status` | `stack`, `status-stack` | No | No | No | — |
| `release-brief` | `release` | Yes | Yes | No | `hal release-brief` |
| `repo-status` | `repo` | No | No | No | `hal repo-status` |
| `ci` | `ci-status` | No | No | No | `hal ci` |
| `doctor-summary` | `doctor` | Yes | Yes | No | `hal doctor` |
| `fix-doctor` | `doctor-fix`, `fix-planner`, `plan-fix` | Yes | Yes | No | `hal fix-doctor` |
| `session` | `memory` | No | No | No | `hal session` |
| `last` | — | No | No | No | `hal last` |
| `remember` | — | No | Yes | No | `hal remember` |
| `timeline` | — | No | No | No | `hal timeline` |
| `memory-path` | `session-path` | No | No | No | `hal memory-path` |
| `memory-status` | `memory-brief` | No | No | No | — |
| `agent-brief` | `agent` | No | No | No | — |
| `hello` | `status-screen` | No | No | No | — |
| `tools` | — | No | No | No | — |
| `models` | `model-profiles` | No | No | No | — |

**AI** — calls Ollama when available; falls back to deterministic output.
**Memory** — writes to `~/.mq-hal/session.jsonl` unless `--no-memory` is
passed.
**Confirm** — prompts before executing. `create_branch` in the router
always confirms regardless.

---

## Router commands (free prompt)

These are handled by the intent router in `scripts/hal.py`. All require
Ollama unless `--no-ai` is passed.

| Flag / form | Description |
| ------------------------------ | ----------------------------------------- |
| `mq-hal "prompt"` | Natural-language intent routing |
| `mq-hal --raw-intent "prompt"` | Print parsed JSON intent, no execution |
| `mq-hal --explain-intent "p"` | Print intent and resolved repo |
| `mq-hal --confirm "prompt"` | Preview command and ask before running |
| `mq-hal --no-ai "prompt"` | Deterministic routing without Ollama |
| `mq-hal --list-repos` | List configured repos |
| `mq-hal --cd <repo>` | Print repo path for shell `cd` |

---

## Router intent allowlist

See `schemas/intent.schema.json` for the formal schema and
`docs/INTENT_CONTRACT.md` for the full safety contract.

| Intent | Safety class | Always confirms |
| --------------- | ------------ | --------------- |
| `help` | read-only | No |
| `list_repos` | read-only | No |
| `print_cd` | read-only | No |
| `pwd` | read-only | No |
| `repo_tree` | read-only | No |
| `git_status` | read-only | No |
| `git_log` | read-only | No |
| `grep_repo` | read-only | No |
| `repo_status_json` | read-only | No |
| `switch_repo` | state-write | No |
| `run_test` | exec | No |
| `open_editor` | exec | No |
| `run_mqlaunch` | mqlaunch-allowlisted | No |
| `create_branch` | repo-write | Yes |
| `refuse` | no-op | — |
