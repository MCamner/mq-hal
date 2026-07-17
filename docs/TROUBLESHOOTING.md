# mq-hal Troubleshooting

Common problems and how to fix them.

---

## Diagnostics first

Run these before anything else:

```bash
mq-hal version        # confirm the installed version
mq-hal config-check   # validate config/repos.json
mq-hal doctor         # system health check
mq-hal stack-status   # full tool-chain state
```

---

## mq-hal: command not found

**Cause:** `bin/mq-hal` is not on `$PATH`.

**Fix:**

```bash
# Add to ~/.zshrc or ~/.bash_profile:
export PATH="$HOME/mq-hal/bin:$PATH"
source ~/.zshrc
```

Or reinstall:

```bash
./install.sh
```

See `docs/INSTALL.md` for full PATH setup steps.

---

## config/repos.json must contain a repos object

**Cause:** The config file is missing, empty, or malformed.

**Fix:**

```bash
mq-hal config-check    # shows which field is invalid
cat config/repos.json  # inspect the file
```

Minimum valid config:

```json
{
  "default_repo": "my-repo",
  "repos": {
    "my-repo": "~/my-repo"
  }
}
```

---

## Ollama not running / no AI output

**Cause:** Ollama is not installed or the service is not running.

**Symptoms:** Commands fall back to deterministic output, or print a warning
about model unavailability.

**Fix:**

```bash
ollama serve           # start the Ollama daemon
mq-hal model-status    # check which models are available
```

All HAL commands work without Ollama — they use deterministic fallback output.
Pass `--no-ai` to force the fallback explicitly:

```bash
mq-hal doctor --no-ai
mq-hal brief --no-ai
```

---

## Model not found / unknown model profile

**Cause:** The requested Ollama model is not pulled locally, or the profile
name is wrong.

**Fix:**

```bash
mq-hal models          # list configured profiles
ollama pull qwen3:4b   # pull the missing model
mq-hal model-test      # verify all configured models respond
```

---

## mq-hal update fails / git pull rejected

**Cause:** Local changes conflict with the upstream branch, or the repo has
a detached HEAD.

**Fix:**

```bash
git status             # check for uncommitted changes
mq-hal update          # shows a preview before pulling
mq-hal update --confirm  # pull after reviewing the preview
```

For a clean reinstall:

```bash
git fetch origin
git reset --hard origin/main
./install.sh
```

---

## release-check fails: GitHub release already exists

**Cause:** `release-check.sh` found a GitHub release tag for the current
`VERSION`. This means the version was already released.

**Fix:** Bump `VERSION` to the next patch level, update `CHANGELOG.md`,
`README.md`, and `docs/index.html`, then re-run `release-check.sh`.

---

## release-check fails: undocumented command

**Cause:** A command was added to `bin/mq-hal` without a matching entry in
`docs/COMMAND_SURFACE.md`.

**Fix:** Add the command to `docs/COMMAND_SURFACE.md` (and optionally
`docs/hal-command-surface.md`), then re-run `release-check.sh`.

---

## Smoke test failure

**Cause:** A regression in a script, or a missing dependency in the test
environment.

**Fix:**

```bash
./tests/<failing-smoke>.sh    # run the specific test for details
python3 -m py_compile scripts/<script>.py   # check Python syntax
mq-hal doctor                 # check runtime dependencies
```

---

## Session memory not saving

**Cause:** `~/.mq-hal/` directory is not writable, or `--no-memory` was
passed.

**Fix:**

```bash
ls -la ~/.mq-hal/           # check the directory exists and is writable
mq-hal memory-path          # print the active session file path
mq-hal session              # read current session (empty = nothing saved yet)
```

Override the state directory for testing:

```bash
MQ_HAL_STATE_DIR=/tmp/hal-test mq-hal brief --sample
```

---

## ask-repo / search returns no results

**Cause:** The repo has not been indexed yet.

**Fix:**

```bash
mq-hal index <repo-name>       # build the local index
mq-hal search "your query"     # retry after indexing
```

---

## Getting more help

- `mq-hal --help` — command overview
- `docs/COMMAND_SURFACE.md` — full command registry
- `docs/INSTALL.md` — installation and PATH setup
- `docs/INTENT_CONTRACT.md` — intent schema and safety classes
- GitHub issues: <https://github.com/MCamner/mq-hal/issues>
