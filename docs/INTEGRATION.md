# HAL Integration Contract

This document defines how `mq-hal` features are designed, tested, released, and exposed through `mqlaunch`.

## Core architecture

```text
mq-hal
  owns: local AI routing, summaries, planning, memory, safety validation

mqlaunch
  owns: terminal UX, menus, command surface, pause behavior, workflow entrypoints

repo-signal
  owns: repository quality scoring, publish readiness, README/docs checks

Ollama
  owns: local language model execution

Git / GitHub CLI
  owns: repo state, CI state, release state
```

Preferred integration path:

```text
User
→ mqlaunch hal <command>
→ terminal/bridges/hal-bridge.sh
→ ~/mq-hal/bin/mq-hal <command>
→ mq-hal scripts
→ safe local tools
```

## Design rule

New HAL features should be built in `mq-hal` first.

`macos-scripts` should only expose them through a thin bridge.

Do not put HAL business logic directly inside `macos-scripts`.

## Feature contract

Every new `mq-hal` feature should include:

```text
1. Script in scripts/
2. Dispatch route in bin/mq-hal
3. Smoke test in tests/
4. README documentation
5. CHANGELOG entry
6. VERSION bump
7. GitHub Actions coverage
8. Optional bridge route in macos-scripts
```

Recommended command shape:

```bash
mq-hal <feature>
mq-hal <feature> --json
mq-hal <feature> --no-ai
mq-hal <feature> --repo <repo-name>
```

If the feature needs CI-safe testing:

```bash
mq-hal <feature> --sample
```

If the feature writes memory:

```bash
mq-hal <feature> --no-memory
MQ_HAL_DISABLE_MEMORY=1 mq-hal <feature>
```

## Bridge contract

`macos-scripts` exposes `mq-hal` features through:

```text
terminal/bridges/hal-bridge.sh
```

The bridge should stay thin.

Good bridge behavior:

```bash
mqlaunch hal doctor
# delegates to:
mq-hal doctor-summary
```

```bash
mqlaunch hal fix-doctor
# delegates to:
mq-hal fix-doctor
```

```bash
mqlaunch hal session
# delegates to:
mq-hal session
```

Bad bridge behavior:

```text
- duplicating mq-hal Python logic
- parsing doctor JSON inside mqlaunch
- adding AI prompts inside mqlaunch
- executing model-generated shell directly
```

## Current command mapping

Current as of v0.13.0. Full reference: `docs/COMMAND_SURFACE.md`.

| MQLaunch command | mq-hal command | Purpose |
| --- | --- | --- |
| `mqlaunch hal "prompt"` | `mq-hal "prompt"` | Natural-language intent routing |
| `mqlaunch hal raw "prompt"` | `mq-hal --raw-intent "prompt"` | Show parsed JSON intent |
| `mqlaunch hal repos` | `mq-hal --list-repos` | List configured repos |
| `mqlaunch hal cd <repo>` | `mq-hal --cd <repo>` | Print repo path |
| `mqlaunch hal brief` | `mq-hal brief` | Repo status snapshot |
| `mqlaunch hal doctor` | `mq-hal doctor-summary` | Summarize doctor JSON |
| `mqlaunch hal fix-doctor` | `mq-hal fix-doctor` | Safe fix plan |
| `mqlaunch hal release-brief` | `mq-hal release-brief` | Release readiness check |
| `mqlaunch hal audit` | `mq-hal audit` | Publish quality audit |
| `mqlaunch hal session` | `mq-hal session` | Show local HAL memory |
| `mqlaunch hal last` | `mq-hal last` | Show latest memory event |
| `mqlaunch hal remember "note"` | `mq-hal remember "note"` | Save manual note |
| `mqlaunch hal memory-path` | `mq-hal memory-path` | Print memory path |
| `mqlaunch hal timeline` | `mq-hal timeline` | Session memory as timeline |
| — | `mq-hal memory-status` | mq-agent memory state |
| — | `mq-hal agent-brief` | mq-agent availability summary |
| — | `mq-hal hello` | Greeting and quick status screen |
| — | `mq-hal stack-status` | Full local stack overview |

## Boundary rules

Every proposed new HAL command must answer: is this HAL's
responsibility, or does it belong in mqlaunch, repo-signal, mq-mcp, or
mq-agent?

| Repo | Role |
| --- | --- |
| `mq-hal` | NL routing, status summaries, safe planning |
| `mqlaunch` | terminal UX, menus, command surface |
| `repo-signal` | repo quality scoring, publish readiness |
| `mq-mcp` | MCP tool surface, local tool execution |
| `mq-agent` | orchestration, agent flows, semantic memory |

mq-hal may:

- call read-only status commands from other tools
- display availability and health summaries
- surface mq-agent memory state as a read-only brief

mq-hal must not:

- orchestrate mq-agent or own mq-mcp execution logic
- implement review, risk scoring, or semantic-memory logic
- route execution around the allowlist for any reason

### Cloud providers

`mq-hal` is local-first: every model call it makes today goes to a local
Ollama endpoint. The terms under which any part of it may talk to an external
model provider are fixed in
[docs/CLOUD_PROVIDER_BOUNDARY.md](CLOUD_PROVIDER_BOUNDARY.md).

> **Network egress is a command-surface decision, not a model-profile side
> effect.**
>
> **A failed provider never silently becomes another provider.**

### Runtime provenance

`mq-agent` owns `mq.stack-provenance.v1` — the observations, the comparisons
between layers, the reason codes, the status and the remediation. `mq-hal`
consumes it and shows it.

> **mq-hal may choose its presentation, but it must preserve every epistemic
> distinction already present in the provenance record, and may derive no new
> one.**

The record separates four absences, and they mean different things. Collapsing
any two of them into one phrase invents a claim nobody observed:

| In the record | Means |
| --- | --- |
| `installed` is null | nobody looked — the ordinary state for a component in another environment |
| `installed.identity_quality` is `unknown` | a layer was observed and could not be identified |
| `running_probe` absent, or `attempted` false | this component has no process to ask |
| `attempted` true, `reachable` false | it was asked and nothing answered |

The wording is `mq-hal`'s to choose. The distinctions are not.

`status`, `reasons` and `summary.next_action` are shown as supplied. `mq-hal`
does not recompute a remedy from the facts beside it: the causal reasoning that
decides between "restart" and "verify the installation, then restart" lives in
`mq-agent`'s reducer, and a second implementation would be free to disagree
with the first.

An unfamiliar reason code must render unchanged. Any colour or severity map
keys on `status`, never on a reason code — otherwise a code added in `mq-agent`
becomes a crash or a silent drop here.

#### Contract, and the transport that carries it

```text
Semantic contract    mq.stack-provenance.v1
Current transport    mq-agent stack provenance --json
```

The command is transport. The contract is the record. Declaring the command in
`.mq/repo-contract.json` would tie the stack graph to one CLI spelling; what is
declared there is `compatibility.consumes: ["mq.stack-provenance.v1"]`.

Transport failure is an `mq-hal` availability problem and never a provenance
result:

```text
mq-agent missing, timing out, exiting non-zero,
or returning output that is not the expected record
        ↓
provenance integration unavailable

        not ↓
a component finding, a status, or a reason code
```

A failed subprocess says something about this machine. It says nothing about
which code the stack is running.

## Tool policy

HAL may inspect and summarize.

HAL may suggest safe commands.

HAL must not auto-repair, auto-delete, auto-reset, auto-commit, auto-push, auto-release, or auto-submit anything.

Execution policy:

```text
read-only first
planning second
manual execution last
```

## Approved tool categories

### Local MQLaunch tools

| Tool | Use |
|---|---|
| `mqlaunch doctor --json` | Health status |
| `mqlaunch selftest` | Smoke/test validation |
| `mqlaunch release-check` | Release readiness |
| `mqlaunch system check` | System overview |
| `mqlaunch perf` | Performance overview |
| `mqlaunch srm ask/search` | Semantic repo memory |
| `mqlaunch ask` | Repo question answering |
| `mqlaunch fix` | Copy-paste command generation |

### Git

| Tool | Use |
|---|---|
| `git status --short` | Working tree status |
| `git diff --stat` | Change summary |
| `git diff` | Detailed local changes |
| `git log --oneline -n 10` | Recent history |
| `git branch --show-current` | Current branch |

### GitHub CLI

| Tool | Use |
|---|---|
| `gh run list` | CI status |
| `gh run view --log-failed` | CI failure details |
| `gh release view` | Release status |
| `gh pr list` | Pull requests |
| `gh issue list` | Issues |

### repo-signal

| Tool | Use |
|---|---|
| `repo-signal publish-checklist .` | Publish readiness |
| `repo-signal readme-score .` | README quality |
| repo-signal roadmap/wiki tools | Documentation planning |

## Safety rules

The model never runs shell directly.

The model may only return structured JSON.

Python validates the intent.

The router executes only allowlisted actions.

Unknown or unsafe actions must be refused.

Blocked command patterns include:

```text
rm
sudo rm
git reset --hard
git clean
push --force
chmod -R
chown -R
kill -9
pkill
security delete
secret deletion
credential changes
```

HAL may recommend inspection commands such as:

```bash
git status --short
git diff --stat
git diff
mqlaunch doctor --json | jq .
mqlaunch selftest
mqlaunch release-check
gh run list --limit 5
gh run view --log-failed
```

## Memory policy

HAL Session Memory is local only.

Default path:

```text
~/.mq-hal/session.jsonl
```

It may store:

```text
doctor_summary
fix_plan
manual note
repo name
timestamp
source
```

Users can disable memory:

```bash
mq-hal doctor-summary --no-memory
mq-hal fix-doctor --no-memory
MQ_HAL_DISABLE_MEMORY=1 mq-hal doctor-summary
```

## Versioning strategy

Use semantic-ish project versions:

```text
PATCH: docs, README, CI fixes, small compatibility fixes
MINOR: new HAL command or new bridge capability
MAJOR: breaking command contract or config layout change
```

Examples:

```text
0.4.0 → session memory feature
0.4.1 → docs/integration/README polish
0.5.0 → timeline feature
0.5.1 → integration contract + docs smoke test
```

`mq-hal` and `macos-scripts` do not need matching version numbers.

Only release `macos-scripts` when the MQLaunch bridge changes.

## Release checklist for mq-hal

Before release:

```bash
git status --short

./tests/smoke.sh
./tests/doctor-summary-smoke.sh
./tests/fix-planner-smoke.sh
./tests/session-memory-smoke.sh
./tests/docs-smoke.sh

python3 -m py_compile \
  scripts/hal.py \
  scripts/doctor_summary.py \
  scripts/fix_planner.py \
  scripts/session_memory.py \
  scripts/timeline.py
```

Then:

```bash
git add .
git commit -m "..."
git push

gh run list --limit 5
gh run watch
```

When CI is green:

```bash
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin vX.Y.Z
```

The tag push **is** the publication. `.github/workflows/release.yml` creates the
release from that version's `CHANGELOG.md` section.

Do not run `gh release create` afterwards. The workflow does not wait, the two
race, and the workflow usually wins with a plain title. Wait for it, then polish
the title if you want one:

```bash
gh release view vX.Y.Z
gh release edit vX.Y.Z --title "mq-hal X.Y.Z — title"
```

```text
tag push    publication
CHANGELOG   release body
human       optional title polish
```

## Release checklist for macos-scripts bridge updates

Only needed when `terminal/bridges/hal-bridge.sh` or MQLaunch docs change.

```bash
cd ~/macos-scripts

bash -n terminal/bridges/hal-bridge.sh
bash -n terminal/launchers/mqlaunch-command-mode.sh
bash -n terminal/launchers/mqlaunch.sh

mqlaunch hal help
mqlaunch hal doctor --no-ai
mqlaunch hal fix-doctor --no-ai
mqlaunch hal session

mqlaunch selftest
mqlaunch doctor --json | jq .
mqlaunch release-check
```

## Recommended roadmap order

Do not add random commands.

Build in this order:

```text
1. Integration contract
2. Brief command
3. Repo status command
4. CI summary command
5. repo-signal audit command
6. release brief command
7. optional MCP integration
```

Recommended next runtime feature:

```bash
mqlaunch hal brief
```

Purpose:

```text
latest doctor summary
latest fix plan
latest note
git status
CI state
release readiness
```

## Definition of done

A HAL feature is done when:

```text
- it works from mq-hal
- it has --json when useful
- it has --no-ai when useful
- it has a smoke test
- it is documented
- CI is green
- release notes exist
- mqlaunch bridge exists if user-facing in MQLaunch
```
