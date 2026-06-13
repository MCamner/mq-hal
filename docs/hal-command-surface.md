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

Operator stack overview from `mq-agent stack cockpit --json`.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal stack-status` |
| Alias | `mq-hal stack` / `mq-hal status` / `mq-hal status-stack` |
| Backend | `scripts/stack_status.py`, `hal/stack.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--legacy` |

Default input: `mq-agent stack cockpit --json`. JSON output preserves the
mq-agent cockpit payload instead of creating a separate mq-hal stack contract.

Legacy fallback: when cockpit data is unavailable, text output falls back to the
pre-v1.3 local collector for `mq-hal`, `mqlaunch`, `repo-signal`, optional
`bridget`, configured repos, and mq-mcp runtime visibility. Use `--legacy` to
force the old local collector.

This command does not execute repairs and does not write session memory.

---

### `release-brief`

Release readiness summary before tagging.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal release-brief` |
| `mqlaunch` | `mqlaunch hal release-brief` |
| Backend | `scripts/release_brief.py` |
| Read-only | Yes |
| Memory write | Yes (saves `release_brief` event on success) |
| Flags | `--repo`, `--json`, `--sample`, `--no-memory`, `--skip-gh`, `--skip-doctor`, `--skip-release-check` |

Checks: VERSION, CHANGELOG entry, README version reference, git tree cleanliness, CI status, latest GitHub release, doctor summary, release-check. Derives overall: `ready` / `needs_review` / `not_ready`.

---

### `release`

Read-only release control center from `mq-agent stack release-check --json`.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal release` |
| Backend | `hal/release.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |
| Subcommands | `gates`, `blockers` |

Shows repo, version, ready state, release score, blockers, and gate status
across the MQ stack. JSON output preserves the mq-agent release-check payload
instead of creating a separate mq-hal release contract.

This command does not run release checks itself, publish releases, create tags,
or write memory.

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

## INSTALL

### `version`

Show the installed mq-hal version and root path.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal version` |
| Alias | `mq-hal --version` |
| Backend | `scripts/version.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json` |

---

### `config-check`

Validate local mq-hal configuration files.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal config-check` |
| Alias | `mq-hal config` |
| Backend | `scripts/config_check.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--strict` |

Checks `config/repos.json`, `config/models.json`, and `config/tools.json`.
Without `--strict`, missing configured repo paths are warnings so a fresh
checkout can still validate its bundled config shape.

---

### `update`

Preview or run a fast-forward update for this checkout.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal update` |
| Alias | `mq-hal upgrade` |
| Backend | `scripts/update.py` |
| Read-only | Dry-run by default |
| Memory write | No |
| Flags | `--json`, `--confirm` |

Without `--confirm`, prints the command it would run. With `--confirm`, runs
`git pull --ff-only` in the mq-hal checkout.

---

## VISUAL

### `analyze-diagram`

Read-only architecture diagram observations.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal analyze-diagram architecture.png` |
| Backend | `scripts/visual_hal.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |

Reports visual file metadata, architecture observations, trust-boundary
prompts, and a draft YAML block. If `mq-image-analyze` is installed locally,
its output is captured as read-only context.

---

### `review-ui`

Read-only UI screenshot critique.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal review-ui screenshot.png` |
| Backend | `scripts/visual_hal.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |

Focuses on hierarchy, spacing, labels, scanability, visible state, and unclear
feedback. It does not infer executable commands from pixels.

---

### `architecture-brief`

Read-only architecture brief draft from visual input.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal architecture-brief architecture.png` |
| Backend | `scripts/visual_hal.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample` |

Summarizes likely architecture intent, actors, boundaries, and unknowns as
observations plus draft YAML. Output is never treated as router intent.

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

### `brain`

Read-only control center for mqobsidian and local HAL memory exports.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal brain` |
| Backend | `hal/brain.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--root` |
| Subcommands | `health`, `recent`, `search`, `ingest-url`, `open`, `sync-status` |

Checks folders under the mqobsidian root: `memory/`, `learn/`, `truth/`, and
`reviews/`. The root is resolved from `MQ_HAL_BRAIN_DIR`, `MQOBSIDIAN_PATH`,
`MQ_OBSIDIAN_PATH`, common home-directory candidates, then `MQ_HAL_STATE_DIR`.

This command only reads, summarizes, displays, and searches existing notes and
exports by default. `ingest-url` bridges to Defuddle with
`defuddle parse <url> --md`, previews by default, and writes only with
`--confirm`. URLs ending in `.md` are rejected because the Defuddle skill says
to fetch Markdown directly. If the Obsidian CLI is available and Obsidian is
open, `open` bridges to `obsidian read`, while `sync-status` bridges to
`obsidian property:set` and requires `--confirm`.

---

### `runtime`

Read-only control center for local runtime services.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal runtime` |
| Backend | `hal/runtime.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--details` |
| Subcommands | `services` |

Checks `Ollama`, `mq-mcp`, `GitHub`, and `brain`. Health statuses are
normalized to `RUNNING`, `WARN`, or `DOWN`; `runtime services` includes the
individual health checks behind each service.

---

### `dashboard`

Terminal dashboard for the HAL operator layer.

| Property | Value |
|---|---|
| `mq-hal` | `mq-hal` / `mq-hal dashboard` |
| Backend | `hal/dashboard.py` |
| Read-only | Yes |
| Memory write | No |
| Flags | `--json`, `--sample`, `--once`, `--no-clear` |
| Keys | `1` Stack, `2` Brain, `3` Release, `4` Runtime, `5` History, `a` Alerts, `r` Refresh, `q` Exit |

The dashboard summarizes Stack, Brain, Release, Runtime, History, and Alerts.
It reuses existing HAL readers and does not introduce a new stack, release, or
runtime contract.

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
