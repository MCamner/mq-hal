# mq-hal

Local HAL-style command router for macOS.

mq-hal lets you ask natural language questions locally through Ollama,
then maps the answer to safe whitelisted terminal actions.

## Current design

User prompt
→ Ollama/Qwen
→ JSON intent
→ Safe Python router
→ git / mqlaunch / repo helpers

## Safety rule

The model never runs shell directly.

It can only return a JSON intent.
The Python router decides what is allowed.

## Quick start

```bash
ollama pull qwen3:4b-instruct

~/mq-hal/bin/mq-hal "visa git status i macos-scripts"
~/mq-hal/bin/mq-hal "kör doctor"
~/mq-hal/bin/mq-hal "byt till repo-signal"
~/mq-hal/bin/mq-hal "visa senaste commits"
```

## Optional model override

```bash
OLLAMA_MODEL=qwen3:4b ~/mq-hal/bin/mq-hal "visa git status"
```

## Repo cd helper

```bash
mq-hal --cd repo-signal
```

Prints the repo path so your shell can cd into it.

Example zsh function:

```bash
mqhcd() {
  local path
  path="$(mq-hal --cd "$1")" || return 1
  cd "$path"
}
```
