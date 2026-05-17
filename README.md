# mq-hal

Local HAL-style command router for macOS.

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.8.1-orange)](VERSION)

`mq-hal` lets you ask natural-language questions locally through Ollama, then maps the answer to safe whitelisted terminal actions.

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
mq-hal repo-status
mq-hal ci
mq-hal "visa git status i macos-scripts"
```

## Demo

```bash
mq-hal "visa git status i macos-scripts"
```

Example output:

```text
HAL: Visar git status.
 M scripts/hal.py
```

```bash
mq-hal --raw-intent "kör doctor"
```

Example output:

```json
{
  "intent": "run_mqlaunch",
  "repo": null,
  "command": "doctor",
  "args": [],
  "message": "Kör mqlaunch doctor."
}
```

## Common commands

```bash
mq-hal brief
mq-hal brief --json
mq-hal release-brief
mq-hal release-brief --json
mq-hal repo-status
mq-hal repo-status --json
mq-hal ci
mq-hal ci --json
mq-hal doctor-summary
mq-hal fix-doctor
mq-hal session
mq-hal last
mq-hal timeline
mq-hal timeline --details
mq-hal remember "release looked good"
mq-hal memory-path
```

Through MQLaunch:

```bash
mqlaunch hal
mqlaunch hal brief
mqlaunch hal release-brief
mqlaunch hal repo-status
mqlaunch hal ci
mqlaunch hal doctor
mqlaunch hal fix-doctor
mqlaunch hal timeline
mqlaunch hal session
```

## HAL Release Brief

Check whether a repo appears ready for release:

```bash
mq-hal release-brief
mq-hal release-brief --json
mq-hal release-brief --repo macos-scripts
```

Skip expensive or external checks:

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
- README badge/reference
- git clean/dirty state
- recent CI status
- latest GitHub release
- doctor summary
- release-check status

## HAL Brief

Get a quick status snapshot of a repo:

```bash
mq-hal brief
```

Machine-readable output:

```bash
mq-hal brief --json
```

Skip GitHub CLI checks:

```bash
mq-hal brief --no-gh
```

Through MQLaunch:

```bash
mqlaunch hal brief
```

Output includes:

- repo path
- git branch
- dirty/clean state
- changed files
- latest commit
- CI status
- latest release
- latest doctor summary
- latest fix plan
- latest session note
- next-step recommendation

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

`repo-status` summarizes:

- branch
- dirty/clean state
- changed files
- recent commits
- latest tags
- safe recommendation

`ci` summarizes:

- recent GitHub Actions runs
- overall CI status
- safe next step

## HAL Doctor Summary

Run a local health check and summarize it:

```bash
mq-hal doctor-summary
```

Machine-readable output:

```bash
mq-hal doctor-summary --json
```

Without AI:

```bash
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
```

Machine-readable output:

```bash
mq-hal fix-doctor --json
```

Without AI:

```bash
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

Show recent memory:

```bash
mq-hal session
```

Show latest memory item:

```bash
mq-hal last
```

Save a manual note:

```bash
mq-hal remember "doctor looked clean after release"
```

Show memory as JSON:

```bash
mq-hal session --json
mq-hal last --json
```

Through MQLaunch:

```bash
mqlaunch hal session
mqlaunch hal last
mqlaunch hal remember "release looked good"
```

What gets saved automatically:

- `doctor_summary`
- `fix_plan`
- manual `note`

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
```

Show more context:

```bash
mq-hal timeline --details
```

Filter by repo:

```bash
mq-hal timeline --repo macos-scripts
```

Filter by type:

```bash
mq-hal timeline --type doctor_summary
mq-hal timeline --type fix_plan
mq-hal timeline --type note
```

Machine-readable output:

```bash
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

## Security

The model only returns a JSON intent from a fixed schema.

The router enforces an explicit allowlist. Unknown or unsafe commands are refused.

`HAL Fix Planner` does not execute repairs. It only prints commands for manual review.

Session Memory stays local in `~/.mq-hal/session.jsonl`.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features.

## License

[MIT](LICENSE)
