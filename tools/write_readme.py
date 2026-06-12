#!/usr/bin/env python3
from pathlib import Path

F = chr(96) * 3

readme = f"""# mq-hal

Local HAL-style command router for macOS.

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.10.0-orange)](VERSION)

`mq-hal` lets you ask natural-language questions locally through Ollama, then maps the answer to safe whitelisted terminal actions.

Live site: <https://mcamner.github.io/mq-hal/>

## How it works

{F}text
User prompt
→ Ollama/Qwen
→ JSON intent
→ Safe Python router
→ git / mqlaunch / repo helpers
{F}

The model never runs shell directly.

It returns a JSON intent. The Python router decides what is allowed.

## Quick start

{F}bash
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
{F}

## Common commands

{F}bash
mq-hal brief
mq-hal release-brief
mq-hal audit
mq-hal stack-status
mq-hal repo-status
mq-hal ci
mq-hal doctor-summary
mq-hal fix-doctor
mq-hal brain
mq-hal session
mq-hal last
mq-hal timeline
mq-hal remember "release looked good"
mq-hal memory-path
mq-hal --raw-intent "kör doctor"
mq-hal --explain-intent "visa git status i repo-signal"
{F}

Through MQLaunch:

{F}bash
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
{F}

## HAL Brief

Get a quick status snapshot of a repo:

{F}bash
mq-hal brief
mq-hal brief --json
mq-hal brief --no-gh
mq-hal brief --repo macos-scripts
{F}

The brief combines git status, CI status, latest release, HAL memory, and a next-step recommendation.

## HAL Release Brief

Check whether a repo appears ready for release:

{F}bash
mq-hal release-brief
mq-hal release-brief --json
mq-hal release-brief --repo macos-scripts
{F}

Skip external or expensive checks:

{F}bash
mq-hal release-brief --skip-gh
mq-hal release-brief --skip-doctor
mq-hal release-brief --skip-release-check
{F}

Through MQLaunch:

{F}bash
mqlaunch hal release-brief
{F}

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

{F}bash
mq-hal audit
mq-hal audit --json
mq-hal audit --repo macos-scripts
{F}

Through MQLaunch:

{F}bash
mqlaunch hal audit
{F}

Audit checks:

- publish checklist score
- README score
- GitHub Pages readiness
- documentation quality signals
- safe next-step recommendation

Requires `repo-signal` locally. Falls back gracefully if unavailable.

## HAL Stack Status

Show the full MQ stack from the operator layer:

{F}bash
mq-hal stack
mq-hal stack --json
mq-hal status
mq-hal stack-status
mq-hal stack-status --json
mq-hal stack-status --sample
{F}

Default input:

{F}bash
mq-agent stack cockpit --json
{F}

Stack Status shows:

- mq-agent
- mq-mcp
- repo-signal
- mqobsidian / brain
- overall stack score

`mq-hal` summarizes stack state only. Review execution and semantic-memory
runtime stay in `mq-mcp`, routed through `mq-agent` where orchestration is
needed.

This command is read-only, does not write session memory, and does not define a
separate stack contract. If mq-agent cockpit data is unavailable, text output
falls back to the legacy local stack collector. Use `--legacy` to force that
local collector.

## HAL Repo Ops

Read-only repository status:

{F}bash
mq-hal repo-status
mq-hal repo-status --json
mq-hal repo-status --repo macos-scripts
{F}

GitHub Actions status:

{F}bash
mq-hal ci
mq-hal ci --json
mq-hal ci --repo macos-scripts
{F}

Through MQLaunch:

{F}bash
mqlaunch hal repo-status
mqlaunch hal ci
{F}

## Brain Control Center

Show mqobsidian and local HAL memory exports:

{F}bash
mq-hal brain
mq-hal brain health
mq-hal brain recent
mq-hal brain search "release"
mq-hal brain --json
{F}

Brain reads:

- `memory/`
- `learn/`
- `truth/`
- `reviews/`

It shows recent notes, recent reviews, latest release export, and folder health.
It only reads existing mqobsidian/HAL memory files; it does not write memory or
run reviews.

## HAL Doctor Summary

Run a local health check and summarize it:

{F}bash
mq-hal doctor-summary
mq-hal doctor-summary --json
mq-hal doctor-summary --no-ai
{F}

Through MQLaunch:

{F}bash
mqlaunch hal doctor
{F}

Flow:

{F}text
mq-hal doctor-summary
→ mqlaunch doctor --json
→ parse doctor JSON
→ summarize with Ollama when available
→ fall back to deterministic local summary when Ollama is unavailable
{F}

## HAL Fix Planner

Create a safe fix plan from HAL Doctor Summary:

{F}bash
mq-hal fix-doctor
mq-hal fix-doctor --json
mq-hal fix-doctor --no-ai
{F}

Through MQLaunch:

{F}bash
mqlaunch hal fix-doctor
{F}

Flow:

{F}text
mq-hal fix-doctor
→ mq-hal doctor-summary --json --no-ai
→ parse findings
→ create safe fix plan
→ print copy-paste commands
→ execute nothing
{F}

## HAL Session Memory

Store local HAL events in:

{F}text
~/.mq-hal/session.jsonl
{F}

Show memory:

{F}bash
mq-hal session
mq-hal last
mq-hal session --json
mq-hal last --json
{F}

Save a manual note:

{F}bash
mq-hal remember "doctor looked clean after release"
{F}

Through MQLaunch:

{F}bash
mqlaunch hal session
mqlaunch hal last
mqlaunch hal remember "release looked good"
{F}

Disable memory for one command:

{F}bash
mq-hal doctor-summary --no-memory
mq-hal fix-doctor --no-memory
{F}

Or disable via environment:

{F}bash
MQ_HAL_DISABLE_MEMORY=1 mq-hal doctor-summary
{F}

## HAL Timeline UI

Show HAL Session Memory as a compact timeline:

{F}bash
mq-hal timeline
mq-hal timeline --details
mq-hal timeline --repo macos-scripts
mq-hal timeline --type doctor_summary
mq-hal timeline --type fix_plan
mq-hal timeline --type note
mq-hal timeline --json
{F}

Through MQLaunch:

{F}bash
mqlaunch hal timeline
mqlaunch hal timeline --details
{F}

## Optional model override

{F}bash
OLLAMA_MODEL=qwen3:4b ~/mq-hal/bin/mq-hal "visa git status"
{F}

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

{F}bash
mqhcd() {{
  if [ $# -ne 1 ]; then
    echo "usage: mqhcd <repo-name>" >&2
    return 2
  fi

  local path
  path="$(mq-hal --cd "$1")" || return $?
  cd "$path" || return $?
}}
{F}

Then:

{F}bash
mqhcd repo-signal
{F}

## Integration contract

New HAL features follow the integration contract:

{F}text
mq-hal owns feature logic
mqlaunch owns command surface
hal-bridge.sh delegates only
tests and docs required before release
{F}

See [docs/INTEGRATION.md](docs/INTEGRATION.md).

## HAL command surface

Full command reference:

See [docs/hal-command-surface.md](docs/hal-command-surface.md).

## Security

The model only returns a JSON intent from a fixed schema.

The router enforces an explicit allowlist. Unknown or unsafe commands are refused.

`HAL Fix Planner` does not execute repairs. It only prints commands for manual review.

Session Memory stays local in `~/.mq-hal/session.jsonl`.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features.

## License

[MIT](LICENSE)
"""

Path("README.md").write_text(readme, encoding="utf-8")
print("README.md written")
