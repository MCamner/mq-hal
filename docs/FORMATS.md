# mq-hal Stable Formats

This document declares the stable on-disk formats for mq-hal v1.0+.
Breaking changes to these formats require a major version bump.

---

## Repo config — `config/repos.json`

Located at `<mq-hal-root>/config/repos.json`.
Override path with `MQ_HAL_CONFIG_PATH`.

```json
{
  "default_repo": "macos-scripts",
  "repos": {
    "macos-scripts": "~/macos-scripts",
    "repo-signal": "~/repo-signal"
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `default_repo` | string | No | Repo used when none is specified in a prompt |
| `repos` | object | Yes | Map of name → path (tilde-expanded) |

Rules:

- `repos` must be a non-empty object.
- Paths support `~` expansion.
- `default_repo` must be a key in `repos` when provided.
- `config-check` validates this file: `mq-hal config-check`.

---

## Session memory — `~/.mq-hal/session.jsonl`

One JSON object per line (JSONL). Appended by HAL commands that write memory.
Override directory with `MQ_HAL_STATE_DIR`.

### Envelope fields (all events)

| Field | Type | Notes |
| --- | --- | --- |
| `timestamp` | string | ISO 8601 with timezone offset |
| `type` | string | Event type (see below) |
| `repo` | string \| null | Active repo at the time |
| `source` | string \| null | Command that wrote the event |
| `payload` | object | Event-specific data |

### Event types

| `type` | Written by | Payload keys |
| --- | --- | --- |
| `brief` | `mq-hal brief` | `repo`, `summary` |
| `audit` | `mq-hal audit` | `repo`, `summary`, `score` |
| `doctor_summary` | `mq-hal doctor-summary` | `summary` (object with `status`) |
| `fix_plan` | `mq-hal fix-doctor` | `plan` (object with `status`) |
| `release_brief` | `mq-hal release-brief` | `repo`, `summary` |
| `note` | `mq-hal remember` | `note`, optional `tag` |

### Example entry

```json
{"timestamp": "2026-05-31T02:49:00+02:00", "type": "note", "repo": "mq-hal", "source": "manual", "payload": {"note": "v0.15.2 released"}}
```

Malformed lines are skipped silently on read.

---

## Timeline output

`mq-hal timeline` reads `session.jsonl` and renders one line per event.

### Text format (default)

```text
<timestamp>  <type:16>        repo=<repo:14> <status or excerpt>
```

`--compact` omits payload details.
`--details` adds a JSON payload excerpt.

### JSON format (`--json`)

Returns a JSON array of event objects. Each element is the raw envelope
(same fields as session memory above) plus a `text` key containing the
rendered one-line summary.

```json
[
  {
    "timestamp": "2026-05-31T02:49:00+02:00",
    "type": "note",
    "repo": "mq-hal",
    "source": "manual",
    "payload": {"note": "v0.15.2 released"},
    "text": "2026-05-31T02:49:00+02:00  note             repo=mq-hal       v0.15.2 released"
  }
]
```

Filters: `--type <type>`, `--repo <name>`, `--since <ISO date>`, `--limit <n>`.
