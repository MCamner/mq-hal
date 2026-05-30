# HAL Command Surface

Reference for every command exposed through `mq-hal` and `mqlaunch hal`.

Each entry lists: what it does, which backend it calls, whether it is read-only, and whether it writes to session memory.

---

## OBSERVE

### `brief`

Quick status snapshot of a configured repo.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal brief` |
| `mqlaunch` | `mqlaunch hal brief` |
| Backend | `scripts/brief.py` |
| Read-only | Yes |
| Memory write | Yes (saves `brief` event on success) |
| Flags | `--repo`, `--json`, `--sample`, `--no-memory` |

Collects: git branch/dirty state, doctor health, CI runs, latest release, last session note. Derives a next-step recommendation.

---

### `audit`

Publish quality and README quality audit via `repo-signal`.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal audit` |
| `mqlaunch` | `mqlaunch hal audit` |
| Backend | `scripts/audit.py` |
| Read-only | Yes |
| Memory write | Yes (saves `audit` event on success) |
| Flags | `--repo`, `--json`, `--sample`, `--no-memory` |
| Requires | `repo-signal` (falls back gracefully if missing) |

Runs `repo-signal publish-checklist --format json` and `repo-signal readme-score`. Derives overall status: `ready` / `needs_review` / `not_ready`. Prints actionable recommendation.

---

### `stack-status`

Local stack overview for `mq-hal`, `repo-signal`, `mq-mcp`, `mqlaunch`, and configured repos.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal stack-status` |
| Alias | `mq-hal stack` / `mq-hal status-stack` |
| Backend | `scripts/stack_status.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |

Checks: local `mq-hal` wrapper, `mqlaunch`, `repo-signal`, optional `bridget`, configured repo paths, git branch and dirty state, VERSION file, and repo-signal publish checklist when available.

Planned mq ecosystem extension: include mq-agent availability and mq-mcp runtime/tool health as read-only status signals. `stack-status` must remain an operator summary; it must not orchestrate mq-agent or execute mq-mcp review flows.

This command does not execute repairs and does not write session memory.

---

### `release-brief`

Release readiness summary before tagging.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal release-brief` |
| `mqlaunch` | `mqlaunch hal release-brief` |
| Alias | `mq-hal release` / `mqlaunch hal release` |
| Backend | `scripts/release_brief.py` |
| Read-only | Yes |
| Memory write | Yes (saves `release_brief` event on success) |
| Flags | `--repo`, `--json`, `--sample`, `--no-memory`, `--skip-gh`, `--skip-doctor`, `--skip-release-check` |

Checks: VERSION, CHANGELOG entry, README version reference, git tree cleanliness, CI status, latest GitHub release, doctor summary, release-check. Derives overall: `ready` / `needs_review` / `not_ready`.

---

### `repo-status`

Read-only git repository state.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal repo-status` |
| `mqlaunch` | `mqlaunch hal repo-status` |
| Alias | `mq-hal repo` / `mqlaunch hal repo` |
| Backend | `scripts/repo_status.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo`, `--json`, `--sample` |

Shows: branch, dirty/clean state, changed file preview, recent commits, latest tags. Safe next-step recommendation.

---

### `ci`

GitHub Actions status.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal ci` |
| `mqlaunch` | `mqlaunch hal ci` |
| Alias | `mqlaunch hal ci-status` |
| Backend | `scripts/ci_status.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo`, `--json`, `--sample`, `--limit` |

Calls `gh run list`. Shows recent run conclusions. Safe next-step recommendation.

---

### `doctor-summary`

Local system health summary.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal doctor-summary` |
| `mqlaunch` | `mqlaunch hal doctor` |
| Backend | `scripts/doctor_summary.py` |
| Read-only | Yes |
| Memory write | Yes (saves `doctor_summary` event) |
| Flags | `--repo`, `--json`, `--sample`, `--no-memory`, `--no-ai` |

Runs `mqlaunch doctor --json`, parses health data. Can use Ollama for a natural-language summary (`--no-ai` to skip).

---

### `timeline`

Compact session event history.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal timeline` |
| `mqlaunch` | `mqlaunch hal timeline` |
| Backend | `scripts/timeline.py` |
| Read-only | Yes (reads memory only) |
| Memory write | No |
| Flags | `--repo`, `--type`, `--limit`, `--details`, `--json` |

Reads `~/.mq-hal/session.jsonl`. Renders a table of event type, repo, time, and status. `--details` adds payload excerpts.

---

## PLAN

### `plan`

Create a structured local plan for a goal.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal plan "goal"` |
| Backend | `scripts/planner.py` |
| Read-only | Yes (generates a plan only) |
| Memory write | No |
| Flags | `--json`, `--out <file>`, `--no-ai`, `--sample`, `--model <profile>` |

Uses Ollama when available and falls back to a deterministic stub plan with
`--no-ai` or when the model is unavailable.

---

### `critic`

Review a saved plan for safety and completeness.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal critic plan.json` |
| Backend | `scripts/critic.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |

Checks rollback, validation, confirmation flags, dangerous commands, known
repos, scope, step count, and visible test/validation coverage. Returns non-zero
when the verdict is `FAIL`.

---

### `execute`

Execute a validated plan step by step.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal execute plan.json --confirm` |
| Backend | `scripts/executor.py` |
| Read-only | No |
| Memory write | No |
| Flags | `--confirm`, `--skip-critic` |

Without `--confirm`, prints a dry-run preview. With `--confirm`, runs a
pre-flight critic check and refuses plans with a `FAIL` verdict. Commands are
parsed with `shlex`, shell operators are refused, and steps marked
`requires_confirm` ask again before running. `--skip-critic` is intended only
for local debugging; command-level shell-operator checks still apply.

---

### `model-status`

Check configured Ollama model availability and latency.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal model-status` |
| Backend | `scripts/model_status.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--profile <name>` |

Calls Ollama's local `/api/tags` endpoint, reports reachability, response
latency, and whether each configured profile model is installed. `--sample`
uses deterministic data for smoke tests.

---

### `model-test`

Run a tiny structured generation test against Ollama.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal model-test` |
| Backend | `scripts/model_test.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--profile <name>` |

Requests a minimal JSON response from the selected profile and verifies that it
matches the expected shape. `--sample` uses deterministic data for smoke tests.

---

### `fix-doctor`

Safe repair plan from the last doctor summary.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal fix-doctor` |
| `mqlaunch` | `mqlaunch hal fix-doctor` |
| Backend | `scripts/fix_planner.py` |
| Read-only | Yes (generates plan only, never executes) |
| Memory write | Yes (saves `fix_plan` event) |
| Flags | `--repo`, `--json`, `--no-memory`, `--no-ai` |

Reads the latest doctor summary from memory. Generates copy-paste shell commands for inspection and verification. Never runs repairs automatically.

---

## MEMORY

### `index`

Build local repo memory for a configured repository.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal index mq-hal` |
| Backend | `scripts/repo_memory.py index` |
| Read-only | No (writes local index under `~/.mq-hal/repo_memory/`) |
| Memory write | Yes |
| Flags | `--json`, `--embeddings`, `--embedding-model <name>` |

Indexes text files only, skips cache/build folders, and never mutates the
repository. `--embeddings` optionally asks local Ollama for embeddings; the
default index is deterministic lexical memory.

---

### `search`

Search indexed repo memory.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal search roadmap --repo mq-hal` |
| Backend | `scripts/repo_memory.py search` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo <name>`, `--limit <n>`, `--json` |

---

### `ask-repo`

Answer from indexed repo memory context.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal ask-repo "what changed in v0.14" --repo mq-hal` |
| Backend | `scripts/repo_memory.py ask-repo` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo <name>`, `--limit <n>`, `--json` |

This is deterministic retrieval, not autonomous reasoning. It returns grounded
context from indexed files and does not invent beyond the local index.

---

### `repo-map`

Summarize indexed repo memory structure.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal repo-map --repo mq-hal` |
| Backend | `scripts/repo_memory.py repo-map` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo <name>`, `--json` |

Shows indexed directories and knowledge tags such as architecture, roadmap,
release-history, tests, and implementation.

---

### `session`

Display local session memory.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal session` |
| `mqlaunch` | `mqlaunch hal session` |
| Backend | `scripts/session_memory.py session` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--repo`, `--type`, `--limit`, `--json` |

---

### `last`

Show the most recent memory event.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal last` |
| `mqlaunch` | `mqlaunch hal last` |
| Backend | `scripts/session_memory.py last` |
| Read-only | Yes |
| Memory write | No |

---

### `remember`

Save a note to session memory.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal remember "text"` |
| `mqlaunch` | `mqlaunch hal remember "text"` |
| Backend | `scripts/session_memory.py remember` |
| Read-only | No |
| Memory write | Yes (saves `note` event) |

---

### `memory-path`

Print the path to the session memory file.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal memory-path` |
| `mqlaunch` | `mqlaunch hal memory-path` |
| Backend | `scripts/session_memory.py path` |
| Read-only | Yes |
| Memory write | No |

---

## DEBUG / AI

### Free prompt

Route a natural-language prompt through the Ollama intent router.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal "visa git status"` |
| `mqlaunch` | `mqlaunch hal "visa git status"` |
| Backend | `scripts/hal.py` |
| Read-only | Depends on routed action |
| Memory write | Depends on routed action |
| Requires | Ollama running locally |

---

### `--raw-intent`

Print the parsed JSON intent without executing it.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal --raw-intent "kör doctor"` |
| `mqlaunch` | `mqlaunch hal raw "kör doctor"` |
| Backend | `scripts/hal.py` |
| Read-only | Yes |
| Memory write | No |

---

### `--explain-intent`

Print the parsed JSON intent plus the resolved repo/path without executing it.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal --explain-intent "visa git status i repo-signal"` |
| Alias | `mq-hal --why "visa git status i repo-signal"` |
| Backend | `scripts/hal.py` |
| Read-only | Yes |
| Memory write | No |

---

### `--confirm`

Preview the resolved command and ask before running it.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal --confirm "kör doctor"` |
| Backend | `scripts/hal.py` |
| Read-only | Depends on confirmed action |
| Memory write | Yes (stores last prompt/intent before execution) |

---

### `--no-ai`

Use deterministic local routing without calling Ollama.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal --no-ai --raw-intent "visa git status i mq-hal"` |
| Backend | `scripts/hal.py` |
| Read-only | Depends on routed action |
| Memory write | Depends on routed action |

Used by smoke tests and as a fallback when Ollama is unavailable for simple prompts.

---

### `grep_repo`

Search a configured repository with safe `rg` arguments.

| Property | Value |
|---|---|
| Prompt | `mq-hal "hitta OLLAMA_MODEL i mq-hal"` |
| Routed command | `rg -n -- <query>` |
| Backend | `scripts/hal.py` |
| Read-only | Yes |
| Memory write | Yes (stores last prompt/intent) |

The router passes the query as an argument list, not a shell string.

---

### `run_test`

Run a detected safe test command for the selected repo.

| Property | Value |
|---|---|
| Prompt | `mq-hal "kör tester i mq-hal"` |
| Backend | `scripts/hal.py` |
| Read-only | No |
| Memory write | Yes (stores last prompt/intent) |

Detection order: `tests/smoke.sh`, `scripts/validate.sh`, `python3 -m pytest`, then `npm test`.

---

### `open_editor`

Open a file or directory under the selected repo in `$VISUAL`, `$EDITOR`, `code`, `open`, or `nano`.

| Property | Value |
|---|---|
| Prompt | `mq-hal "öppna README.md i mq-hal"` |
| Backend | `scripts/hal.py` |
| Read-only | No |
| Memory write | Yes (stores last prompt/intent) |

Paths are resolved under the selected repo and paths outside the repo are refused.

---

### `create_branch`

Create a new git branch in the selected repo after preview confirmation.

| Property | Value |
|---|---|
| Prompt | `mq-hal "skapa branch feature/demo i mq-hal"` |
| Routed command | `git checkout -b <branch>` |
| Backend | `scripts/hal.py` |
| Read-only | No |
| Memory write | Yes (stores last prompt/intent) |

Branch names are validated and the command always asks before running, even without `--confirm`.

---

### `--list-repos`

List all configured repos.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal --list-repos` |
| `mqlaunch` | `mqlaunch hal repos` |
| Backend | `scripts/hal.py` |
| Read-only | Yes |
| Memory write | No |

---

## Memory behaviour summary

| Command | Writes memory |
|---|---|
| `brief` | Yes — `brief` event |
| `audit` | Yes — `audit` event |
| `stack-status` | No |
| `release-brief` | Yes — `release_brief` event |
| `repo-status` | No |
| `ci` | No |
| `doctor-summary` | Yes — `doctor_summary` event |
| `timeline` | No |
| `fix-doctor` | Yes — `fix_plan` event |
| `session` | No |
| `last` | No |
| `remember` | Yes — `note` event |
| `memory-path` | No |
| `index` | Yes — local repo memory index |
| `search` | No |
| `ask-repo` | No |
| `repo-map` | No |
| `tools` | No |
| `models` | No |
| `model-status` | No |
| `model-test` | No |
| `plan` | No |
| `critic` | No |
| `execute` | No |
| Free prompt | Depends on action |
| `--raw-intent` | No |
| `--explain-intent` | No |
| `grep_repo` | Yes — last prompt/intent |
| `run_test` | Yes — last prompt/intent |
| `open_editor` | Yes — last prompt/intent |
| `create_branch` | Yes — last prompt/intent |

Feature event writes respect `--no-memory` and `MQ_HAL_DISABLE_MEMORY=1` where those flags exist.
The natural-language router also keeps the latest prompt/intent in `~/.mq-hal/state.json`
so short follow-ups can be routed with context.
