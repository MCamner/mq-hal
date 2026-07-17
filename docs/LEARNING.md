# mq-hal Learn Layer

`mq-hal learn` is a local lesson store for verified learnings from Codex,
Claude, or manual work. Lessons are written once and stay local — they are
never promoted automatically to `AGENTS.md`, `CLAUDE.md`, or any router
configuration.

---

## Commands

### `mq-hal learn add`

Add a verified lesson.

```bash
mq-hal learn add \
  --repo mq-hal \
  --source manual \
  --task "version sync before release" \
  --lesson "Always update README badge, CHANGELOG and docs/index.html together." \
  --validation "release-check --dry-run passes"
```

| Flag | Required | Description |
| --- | --- | --- |
| `--source` | Yes | `codex`, `claude`, or `manual` |
| `--task` | Yes | What was being done |
| `--lesson` | Yes | What was learned |
| `--repo` | No | Repo the lesson applies to |
| `--validation` | No | How the lesson was verified |
| `--json` | No | JSON output |

Secret-like values (`api_key: ...`, `token: ...`, `ghp_...`, `sk-...`)
are redacted to `[REDACTED]` before the lesson is saved.

---

### `mq-hal learn list`

List all lessons.

```bash
mq-hal learn list
mq-hal learn list --repo mq-hal
mq-hal learn list --source claude
mq-hal learn list --json
```

---

### `mq-hal learn show <id>`

Show a lesson by id (prefix match).

```bash
mq-hal learn show b9f18cd7
mq-hal learn show b9f1
mq-hal learn show b9f1 --json
```

---

### `mq-hal learn search "<query>"`

Full-text search across task, lesson, validation and repo fields.

```bash
mq-hal learn search "version sync"
mq-hal learn search "README" --json
```

---

### `mq-hal learn summarize`

Count lessons by source and repo.

```bash
mq-hal learn summarize
mq-hal learn summarize --repo mq-hal
mq-hal learn summarize --json
```

---

## Storage format

Lessons are stored in `~/.mq-hal/learn/lessons.jsonl`.
Override the directory with `MQ_HAL_STATE_DIR`.

Each line is a JSON object:

```json
{
  "id": "b9f18cd7",
  "timestamp": "2026-05-31T03:20:00+02:00",
  "repo": "mq-hal",
  "source": "manual",
  "task": "version sync before release",
  "lesson": "Always update README badge, CHANGELOG and docs/index.html together.",
  "validation": "release-check --dry-run passes"
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | 8-char UUID prefix, unique per lesson |
| `timestamp` | string | ISO 8601 with timezone |
| `repo` | string \| null | Repo the lesson applies to |
| `source` | string | `codex`, `claude`, or `manual` |
| `task` | string | What was being done |
| `lesson` | string | What was learned |
| `validation` | string | How it was verified (may be empty) |

---

## Safety rules

- Local only — no upload, no sync, no external calls
- Secret patterns redacted before write (`api_key:`, `token:`, `bearer`,
  `ghp_*`, `sk-*`)
- No command execution
- No router mutation — `ALLOWED_INTENTS` and `ALLOWED_MQLAUNCH` are never
  modified
- No allowlist mutation
- No automatic promotion to `AGENTS.md`, `CLAUDE.md`, or any config file

---

## Distinction from session memory

| Layer | Where | Written by | Purpose |
| --- | --- | --- | --- |
| Session memory | `~/.mq-hal/session.jsonl` | HAL commands (`brief`, `audit`, …) | Event log for timeline |
| Learn layer | `~/.mq-hal/learn/lessons.jsonl` | `mq-hal learn add` (always manual) | Verified learnings for future reference |

Session memory records what HAL did. The learn layer records what you learned.
