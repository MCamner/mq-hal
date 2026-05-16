# mq-hal

**Local HAL-style command router for macOS.**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.1-orange)](VERSION)

mq-hal lets you ask natural language questions locally through Ollama,
then maps the answer to safe whitelisted terminal actions.

**[Live site → mcamner.github.io/mq-hal](https://mcamner.github.io/mq-hal/)**

---

## How it works

```text
User prompt → Ollama/Qwen → JSON intent → Safe Python router → git / mqlaunch / repo helpers
```

The model **never runs shell directly**. It returns a JSON intent.
The Python router decides what is allowed.

---

## Demo

```console
$ mq-hal "visa git status i macos-scripts"
HAL: Visar git status.
M  scripts/hal.py

$ mq-hal --raw-intent "kör doctor"
{
  "intent": "run_mqlaunch",
  "repo": null,
  "command": "doctor",
  "args": [],
  "message": "Kör mqlaunch doctor."
}

$ mq-hal "visa senaste commits"
HAL: Visar de senaste commit-loggarna.
fe4704a update project files
d306b68 fix: resolve symlinks in bin wrapper via python realpath
5de240b feat: initial mq-hal v0.1
```

Screenshots: [docs/screenshots/](docs/screenshots/)

---

## Quick start

```bash
# 1. Install Ollama
brew install ollama
brew services start ollama

# 2. Pull model
ollama pull qwen3:4b-instruct

# 3. Clone and link binary
git clone https://github.com/MCamner/mq-hal.git ~/mq-hal
ln -s ~/mq-hal/bin/mq-hal ~/bin/mq-hal

# 4. Edit config/repos.json with your repos, then:
mq-hal "visa git status i macos-scripts"
mq-hal "kör doctor"
mq-hal "byt till repo-signal"
```

---

## Optional model override

```bash
OLLAMA_MODEL=qwen3:4b ~/mq-hal/bin/mq-hal "visa git status"
```

---

## Repo cd helper

Add to `~/.zshrc`:

```bash
mqhcd() {
  if [ $# -ne 1 ]; then
    echo "usage: mqhcd <repo-name>" >&2
    return 2
  fi
  local path
  path="$(mq-hal --cd "$1")" || return $?
  cd "$path" || return $?
}
```

Then:

```bash
mqhcd repo-signal
```

---

## HAL Doctor Summary

Run a local health check and summarize it:

```bash
mq-hal doctor-summary
```

Machine-readable output:

```bash
mq-hal doctor-summary --json
```

Without AI (deterministic fallback):

```bash
mq-hal doctor-summary --no-ai
```

Through MQLaunch after installing the bridge:

```bash
mqlaunch hal doctor
```

```text
mq-hal doctor-summary
→ mqlaunch doctor --json
→ parse doctor JSON
→ summarize with Ollama when available
→ fall back to deterministic local summary when Ollama is unavailable
```

---

## HAL Fix Planner

Create a safe fix plan from HAL Doctor Summary:

```bash
mq-hal fix-doctor
```

Machine-readable output:

```bash
mq-hal fix-doctor --json
```

Without AI:

```bash
mq-hal fix-doctor --no-ai
```

Through MQLaunch after installing the bridge:

```bash
mqlaunch hal fix-doctor
```

```text
mq-hal fix-doctor
→ mq-hal doctor-summary --json --no-ai
→ parse findings
→ create safe fix plan
→ print copy-paste commands
→ execute nothing
```

---

## Security

The model only returns a JSON intent from a fixed schema.
The router enforces an explicit allowlist — unknown or unsafe commands get `refuse`.
No shell injection is possible.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features.

---

## License

[MIT](LICENSE)
