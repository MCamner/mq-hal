# HAL Intent Contract

The intent contract defines the JSON structure the Ollama model must
return and the Python router validates before executing any action.

The model never executes commands directly.
The router only executes what the intent contract allows.

The formal JSON Schema is at `schemas/intent.schema.json`.

---

## Schema version

Every valid intent must include:

```json
{ "schema": "mq-hal.intent.v1" }
```

Intents with a missing or incorrect schema field are rejected.

---

## Intent shape

```json
{
  "schema": "mq-hal.intent.v1",
  "intent": "git_status",
  "repo": "macos-scripts",
  "command": null,
  "args": [],
  "message": "Visar git status."
}
```

---

## Field reference

| Field | Type | Required | Description |
| ------- | -------------- | -------- | -------------------------------------- |
| `schema` | string | Yes | Must be `mq-hal.intent.v1` |
| `intent` | string | Yes | Routed action — see intent types below |
| `repo` | string or null | Yes | Repo key from `config/repos.json`, or null |
| `command` | string or null | Yes | `run_mqlaunch` subcommand; null otherwise |
| `args` | string array | Yes | Arguments for the routed command |
| `message` | string | Yes | Human-readable description of the action |

Additional properties are rejected.

---

## Intent types

### Read-only

| Intent | Description |
| -------------- | ----------------------------------------- |
| `help` | Print mq-hal command reference |
| `list_repos` | List configured repos |
| `print_cd` | Print repo path (for shell cd alias) |
| `pwd` | Print active repo working directory |
| `repo_tree` | List files under the active repo |
| `git_status` | Run `git status --short` in target repo |
| `git_log` | Run `git log --oneline -n 8` in target repo |
| `grep_repo` | Run `rg -n -- <query>` in target repo |
| `repo_status_json` | Structured inspect and doctor JSON |

### State-write

| Intent | Description |
| -------------- | ----------------------------------------- |
| `switch_repo` | Set active repo in `~/.mq-hal/state.json` |

### Executes commands

| Intent | Description |
| -------------- | ----------------------------------------- |
| `run_test` | Run the detected safe test command |
| `open_editor` | Open a file under the repo in `$EDITOR` |
| `run_mqlaunch` | Run an allowlisted `mqlaunch` command |

### Repo-write (always requires confirmation)

| Intent | Description |
| -------------- | ----------------------------------------- |
| `create_branch` | Create a branch with `git checkout -b` |

### Safety

| Intent | Description |
| -------------- | ----------------------------------------- |
| `refuse` | Refuse the prompt — no execution occurs |

---

## Allowed mqlaunch commands

For `run_mqlaunch`, the `command` field must match one of:

```text
doctor
release-check
selftest
perf
system-check
demo
```

Unknown mqlaunch commands are rejected with exit code 2.

---

## Safety contract

### Unknown intent

Any model output where `intent` is not in the allowlist is normalized to
`refuse` by the router before execution.

### Malformed JSON

If the model returns non-JSON or unparseable JSON, the router falls back
to `refuse`. Execution does not occur.

### Path escapes

For intents that resolve a file path (e.g. `open_editor`), paths outside
the target repo are rejected with exit code 2.

### Repo key validation

If `repo` is not a key in `config/repos.json`, the router falls back to
the active repo from state. It does not error.

### Branch name validation

For `create_branch`, branch names are validated with a strict allowlist:
alphanumeric, `.`, `_`, `-`, `/`. Names starting with `-`, `/`, or `.`
are rejected.

---

## Rejection behavior

| Condition | Result |
| ------------------------------- | -------------------------------- |
| Unknown intent value | Normalized to `refuse` |
| Missing required field | Intent treated as `refuse` |
| Non-JSON model output | Router returns `refuse` |
| Unknown mqlaunch command | Rejected, exit 2 |
| Path outside repo | Rejected, exit 2 |
| Invalid branch name | Rejected, exit 2 |

---

## Valid intent examples

```json
{"schema":"mq-hal.intent.v1","intent":"git_status","repo":"macos-scripts","command":null,"args":[],"message":"Visar git status."}
```

```json
{"schema":"mq-hal.intent.v1","intent":"run_mqlaunch","repo":null,"command":"doctor","args":[],"message":"Kör mqlaunch doctor."}
```

```json
{"schema":"mq-hal.intent.v1","intent":"grep_repo","repo":"mq-hal","command":null,"args":["OLLAMA_MODEL"],"message":"Söker."}
```

```json
{"schema":"mq-hal.intent.v1","intent":"create_branch","repo":"mq-hal","command":null,"args":["feature/hal-router"],"message":"Skapar branch."}
```

## Rejected intent examples

Unknown action — normalized to `refuse`:

```json
{"schema":"mq-hal.intent.v1","intent":"rm_rf","repo":null,"command":null,"args":[],"message":""}
```

Unknown mqlaunch command — rejected with exit 2:

```json
{"schema":"mq-hal.intent.v1","intent":"run_mqlaunch","repo":null,"command":"rm -rf /","args":[],"message":""}
```

Path escape — rejected with exit 2:

```json
{"schema":"mq-hal.intent.v1","intent":"open_editor","repo":"mq-hal","command":null,"args":["../../etc/passwd"],"message":""}
```
