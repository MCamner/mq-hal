# mq-hal

Local HAL-style command router for macOS.

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.12.0-orange)](VERSION)

`mq-hal` lets you ask natural-language questions locally through Ollama,
then maps the answer to safe whitelisted terminal actions.

Live site: <https://mcamner.github.io/mq-hal/>

## How it works

```text
User prompt
→ Ollama/Qwen
→ JSON intent
→ Safe Python router
→ git / mqlaunch / repo helpers
```

The model never runs shell directly.

It returns a JSON intent. The Python router decides what is allowed.

## Quick start

```bash
# 1. Install Ollama
brew install ollama
brew services start ollama

# 2. Pull model
ollama pull qwen3:4b-instruct

# 3. Clone and link binary
git clone https://github.com/MCamner/mq-hal.git ~/mq-hal
mkdir -p ~/bin
ln -sf ~/mq-hal/bin/mq-hal ~/bin/mq-hal

# 4. Edit config/repos.json with your repos, then:
mq-hal brief
mq-hal release-brief
mq-hal audit
mq-hal stack-status
mq-hal repo-status
mq-hal ci
mq-hal "visa git status i macos-scripts"
mq-hal "hitta OLLAMA_MODEL i mq-hal"
mq-hal "kör tester i mq-hal"
mq-hal --confirm "kör doctor"
```

## Common commands

```bash
mq-hal brief
mq-hal release-brief
mq-hal audit
mq-hal stack-status
mq-hal repo-status
mq-hal ci
mq-hal doctor-summary
mq-hal fix-doctor
mq-hal session
mq-hal last
mq-hal timeline
mq-hal remember "release looked good"
mq-hal memory-path
mq-hal --raw-intent "kör doctor"
mq-hal --explain-intent "visa git status i repo-signal"
```

Through MQLaunch:

```bash
mqlaunch hal
mqlaunch hal brief
mqlaunch hal release-brief
mqlaunch hal audit
mqlaunch hal repo-status
mqlaunch hal ci
mqlaunch hal doctor
mqlaunch hal fix-doctor
mqlaunch hal timeline
mqlaunch hal session
```

## HAL Brief

Get a quick status snapshot of a repo:

```bash
mq-hal brief
mq-hal brief --json
mq-hal brief --no-gh
mq-hal brief --repo macos-scripts
```

The brief combines git status, CI status, latest release, HAL memory,
and a next-step recommendation.

## HAL Release Brief

Check whether a repo appears ready for release:

```bash
mq-hal release-brief
mq-hal release-brief --json
mq-hal release-brief --repo macos-scripts
```

Skip external or expensive checks:

```bash
mq-hal release-brief --skip-gh
mq-hal release-brief --skip-doctor
mq-hal release-brief --skip-release-check
```

Through MQLaunch:

```bash
mqlaunch hal release-brief
```

The release brief checks:

- VERSION
- CHANGELOG entry
- README badge or version reference
- git clean/dirty state
- recent CI status
- latest GitHub release
- doctor summary
- release-check status

## HAL Audit

Check publish quality and README quality via `repo-signal`:

```bash
mq-hal audit
mq-hal audit --json
mq-hal audit --repo macos-scripts
```

Through MQLaunch:

```bash
mqlaunch hal audit
```

Audit checks:

- publish checklist score
- README score
- GitHub Pages readiness
- documentation quality signals
- safe next-step recommendation

Requires `repo-signal` locally. Falls back gracefully if unavailable.

## HAL Stack Status

Show the local AI/repo tooling stack:

```bash
mq-hal stack-status
mq-hal stack-status --json
mq-hal stack-status --sample
```

Stack Status checks:

- mq-hal wrapper
- mqlaunch availability
- repo-signal availability
- mq-mcp-adjacent runtime visibility as the integration matures
- optional bridget availability
- configured repo paths
- git branch and dirty state
- VERSION file
- repo-signal publish checklist when available

`mq-hal` summarizes stack state only. Review execution and semantic-memory
runtime stay in `mq-mcp`, routed through `mq-agent` where orchestration is
needed.

This command is read-only and does not write session memory.

## HAL Repo Ops

Read-only repository status:

```bash
mq-hal repo-status
mq-hal repo-status --json
mq-hal repo-status --repo macos-scripts
```

GitHub Actions status:

```bash
mq-hal ci
mq-hal ci --json
mq-hal ci --repo macos-scripts
```

Through MQLaunch:

```bash
mqlaunch hal repo-status
mqlaunch hal ci
```

## HAL Doctor Summary

Run a local health check and summarize it:

```bash
mq-hal doctor-summary
mq-hal doctor-summary --json
mq-hal doctor-summary --no-ai
```

Through MQLaunch:

```bash
mqlaunch hal doctor
```

Flow:

```text
mq-hal doctor-summary
→ mqlaunch doctor --json
→ parse doctor JSON
→ summarize with Ollama when available
→ fall back to deterministic local summary when Ollama is unavailable
```

## HAL Fix Planner

Create a safe fix plan from HAL Doctor Summary:

```bash
mq-hal fix-doctor
mq-hal fix-doctor --json
mq-hal fix-doctor --no-ai
```

Through MQLaunch:

```bash
mqlaunch hal fix-doctor
```

Flow:

```text
mq-hal fix-doctor
→ mq-hal doctor-summary --json --no-ai
→ parse findings
→ create safe fix plan
→ print copy-paste commands
→ execute nothing
```

## HAL Session Memory

Store local HAL events in:

```text
~/.mq-hal/session.jsonl
```

Show memory:

```bash
mq-hal session
mq-hal last
mq-hal session --json
mq-hal last --json
```

Save a manual note:

```bash
mq-hal remember "doctor looked clean after release"
```

Through MQLaunch:

```bash
mqlaunch hal session
mqlaunch hal last
mqlaunch hal remember "release looked good"
```

Disable memory for one command:

```bash
mq-hal doctor-summary --no-memory
mq-hal fix-doctor --no-memory
```

Or disable via environment:

```bash
MQ_HAL_DISABLE_MEMORY=1 mq-hal doctor-summary
```

## HAL Timeline UI

Show HAL Session Memory as a compact timeline:

```bash
mq-hal timeline
mq-hal timeline --details
mq-hal timeline --repo macos-scripts
mq-hal timeline --type doctor_summary
mq-hal timeline --type fix_plan
mq-hal timeline --type note
mq-hal timeline --json
```

Through MQLaunch:

```bash
mqlaunch hal timeline
mqlaunch hal timeline --details
```

## Optional model override

```bash
OLLAMA_MODEL=qwen3:4b ~/mq-hal/bin/mq-hal "visa git status"
```

## Natural-language routing

`mq-hal "prompt"` routes through Ollama by default. The router now supports:

- repo status and recent log
- repo tree preview
- safe `rg` search in configured repos
- safe test command detection
- opening files under the selected repo in `$EDITOR`
- creating a git branch after preview confirmation
- allowlisted `mqlaunch` commands

Use `--raw-intent` to inspect only the JSON intent, `--explain-intent` to show
the resolved repo/path, and `--confirm` to preview routed commands before they
run.

If Ollama is unavailable, simple prompts can fall back to deterministic local
routing. Use `--no-ai` to force that path for smoke tests or debugging.

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

## Integration contract

New HAL features follow the integration contract:

```text
mq-hal owns feature logic
mqlaunch owns command surface
hal-bridge.sh delegates only
tests and docs required before release
```

See [docs/INTEGRATION.md](docs/INTEGRATION.md).

## HAL command surface

Full command reference: [docs/hal-command-surface.md](docs/hal-command-surface.md).

Command registry: [docs/COMMAND_SURFACE.md](docs/COMMAND_SURFACE.md).

Intent contract: [docs/INTENT_CONTRACT.md](docs/INTENT_CONTRACT.md).

Formal JSON Schema: [schemas/intent.schema.json](schemas/intent.schema.json).

## Proof

- Model returns a JSON intent only — the Python router decides what is allowed
- Router enforces an explicit allowlist — unknown or unsafe commands are refused
- HAL Fix Planner prints copy-paste repair plans but executes nothing
- Session Memory stays local in `~/.mq-hal/session.jsonl` — nothing is sent externally
- Intent contract is machine-validated: `schemas/intent.schema.json` enum
  must match `ALLOWED_INTENTS` in the router on every smoke run
- Command surface is checked: `tools/check-command-docs.sh` fails if any
  command is added without documentation
- Smoke tests cover: doctor summary, fix planner, session memory, timeline,
  repo ops, CI status, release brief, audit, stack status, hal router,
  intent schema contract, router safety, and docs
- README markdown guard (`tools/markdown_guard.py`) blocks flattened
  rendering regressions on every push
- CI runs on `macos-latest` — all smoke tests verified natively on macOS

## Security

The model only returns a JSON intent from a fixed schema.

The router enforces an explicit allowlist. Unknown or unsafe commands are refused.

`HAL Fix Planner` does not execute repairs. It only prints commands for manual review.

Session Memory stays local in `~/.mq-hal/session.jsonl`.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features.

## License

[MIT](LICENSE)
