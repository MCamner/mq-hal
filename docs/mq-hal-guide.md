# mq-hal Guide

## Purpose

`mq-hal` is the MQ-stack operator layer.

It gives a human-friendly command surface for local automation, repo status,
release status, runtime health, memory/brain state, and safe natural-language
routing.

It should help the operator answer:

```text
What is the current state?
What is blocked?
What should I check next?
What can be safely routed?
What requires confirmation?
```

## Role in the MQ stack

```text
mqlaunch
  -> starts commands and menus

mq-hal
  -> operator-facing summaries, routing, dashboard, safe previews

mq-agent
  -> orchestration, stack gates, release checks, context export

mq-mcp
  -> bounded tool runtime, review contracts, learning tools

repo-signal
  -> repo health, readiness, README/docs scoring

mqobsidian
  -> durable memory, truth exports, context cards, token-reduction layer
```

`mq-hal` should not become the runtime brain or the orchestration engine.

It should stay small, readable, predictable, and safe.

## Core safety model

`mq-hal` follows this pattern:

```text
User prompt
  -> local model / deterministic parser
  -> JSON intent
  -> Python router
  -> allowlisted action
  -> preview or execute with confirmation
```

Rules:

* The model never runs shell directly.
* Unknown commands are refused.
* Unsafe shell operators should be rejected.
* Destructive or write actions require explicit confirmation.
* `fix-doctor` prints repair plans but executes nothing.
* `execute` should dry-run by default.
* Local memory stays local.

See `docs/INTENT_CONTRACT.md` and `schemas/intent.schema.json` for the formal
router safety contract.

## Install / setup

Clone and link:

```bash
git clone https://github.com/MCamner/mq-hal.git ~/mq-hal
cd ~/mq-hal

./install.sh
mq-hal version
mq-hal config-check
```

Optional local model setup:

```bash
brew install ollama
brew services start ollama
ollama pull qwen3:4b-instruct
```

## First commands to learn

### Basic status

```bash
mq-hal brief
mq-hal brief --json
mq-hal brief --repo macos-scripts
```

Use this when you want a quick repo snapshot.

### Stack status

```bash
mq-hal stack-status
mq-hal stack-status --json
mq-hal stack-status --sample
```

Use this when you want the MQ-stack operator view.

Expected stack areas:

```text
mq-agent
mq-mcp
repo-signal
mqobsidian / brain
overall stack score
```

`stack-status` uses `mq-agent stack cockpit --json` as its default input and
falls back safely when that is unavailable.

### Runtime status

```bash
mq-hal runtime
mq-hal runtime services
mq-hal runtime --json
```

Use this to check local service health:

```text
Ollama
mq-mcp
GitHub
brain / mqobsidian
```

### Release status

```bash
mq-hal release-brief
mq-hal release-brief --json
mq-hal release

mq-hal release gates
mq-hal release blockers
```

Use this before preparing releases.

### Repo audit

```bash
mq-hal audit
mq-hal audit --json
mq-hal audit --repo macos-scripts
```

Use this when checking README/docs/publish quality through `repo-signal`.

## Brain / mqobsidian commands

Use `brain` commands to inspect MQ memory and exported knowledge.

```bash
mq-hal brain
mq-hal brain health
mq-hal brain recent
mq-hal brain search "release"
mq-hal brain open "mq-stack/05_RELEASE_STATUS.md"
mq-hal brain --json
```

`mq-hal brain` reads memory state and shows it clearly.

It should not become the writer of durable architecture memory unless the
command is explicitly designed and confirmed.

## Natural-language routing

Examples:

```bash
mq-hal "visa git status i repo-signal"
mq-hal "hitta OLLAMA_MODEL i mq-hal"
mq-hal "kör tester i mq-hal"
```

Inspect intent only:

```bash
mq-hal --raw-intent "kör doctor"
mq-hal --explain-intent "visa git status i repo-signal"
```

Require confirmation:

```bash
mq-hal --confirm "kör doctor"
```

Use natural language for small local operations only.

Do not use it for broad architecture changes without first creating a plan.

## Plan, critic, execute

For controlled work:

```bash
mq-hal plan "update release docs" --out plan.json
mq-hal critic plan.json
mq-hal execute plan.json
mq-hal execute plan.json --confirm
```

Expected flow:

```text
plan
  -> save structured plan
  -> critic review
  -> dry-run preview
  -> execute only with --confirm
```

Rules:

* `execute` must refuse failed critic plans.
* `execute` must preview by default.
* `--confirm` is required for execution.
* Steps marked as confirmation-required must ask again.

## Doctor and fix planner

Summarize local health:

```bash
mq-hal doctor-summary
mq-hal doctor-summary --json
mq-hal doctor-summary --no-ai
```

Create a safe fix plan:

```bash
mq-hal fix-doctor
mq-hal fix-doctor --json
mq-hal fix-doctor --no-ai
```

Important:

```text
fix-doctor prints commands.
fix-doctor does not execute repairs.
```

## Timeline and session memory

Show local HAL session memory:

```bash
mq-hal session
mq-hal last
mq-hal timeline
mq-hal timeline --details
mq-hal history
mq-hal alerts
```

Save a manual note:

```bash
mq-hal remember "release looked good"
```

Disable memory for one command:

```bash
mq-hal doctor-summary --no-memory
mq-hal fix-doctor --no-memory
```

Or via environment:

```bash
MQ_HAL_DISABLE_MEMORY=1 mq-hal doctor-summary
```

## Repo memory

Build and query a local deterministic repo index:

```bash
mq-hal index mq-hal
mq-hal search roadmap --repo mq-hal
mq-hal ask-repo "what is planned next" --repo mq-hal
mq-hal repo-map --repo mq-hal
```

Use this before asking an AI tool to scan whole repos.

The goal is to reduce unnecessary context reads.

## Visual HAL

Use visual commands for architecture diagrams and screenshots:

```bash
mq-hal analyze-diagram architecture.png
mq-hal review-ui screenshot.png
mq-hal architecture-brief architecture.png
```

Rules:

* Visual input is read-only.
* Visual findings should not become executable intent.
* If `mq-image-analyze` is available, it can provide extra context.
* If not available, HAL should fall back to deterministic checklists.

## mqlaunch integration

Common mqlaunch entrypoints:

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

Recommended new mqlaunch entries now that `mqobsidian` is a repo:

```bash
mqlaunch hal brain
mqlaunch hal context
mqlaunch hal context-budget
mqlaunch hal latest-pack
```

## Recommended new context commands (proposed — not yet implemented)

These are proposed additions so `mq-hal` stays in phase with `mqobsidian`
token reduction. They are **not** in the current command surface.

```bash
mq-hal context
mq-hal context status
mq-hal context latest-pack
mq-hal context budget
mq-hal context open
```

Purpose:

```text
Show whether mqobsidian context packs exist.
Show whether token budget passes.
Show latest task-pack.
Open relevant context files.
Do not generate context packs directly unless delegated to mq-agent.
```

Ownership should stay like this:

```text
mq-hal
  -> shows context status

mq-agent
  -> generates context packs

mqobsidian
  -> stores schemas, templates, context cards, roadmap
```

## Recommended dashboard sections

The TUI dashboard should show:

```text
1 Stack
2 Brain
3 Release
4 Runtime
5 History
6 Context
a Alerts
r Refresh
q Exit
```

New Context section (proposed):

```text
Context Pack
  mqobsidian: found / missing
  latest task-pack: found / missing
  token budget: pass / fail
  target: codex / claude / both
  last generated: timestamp
```

## When to use mq-hal

Use `mq-hal` when you want:

* a quick operator summary
* safe repo status
* stack status
* release readiness
* runtime health
* mqobsidian / brain health
* local session memory
* safe natural-language routing
* dry-run repair plans
* dashboard view

## When not to use mq-hal

Do not use `mq-hal` to own:

* stack orchestration
* release gates
* semantic review runtime
* durable memory schema design
* endpoint execution
* UMS operations
* context-pack generation logic
* long-term architecture storage

Those belong elsewhere:

```text
mq-agent      orchestration
mq-mcp        runtime/review/learning
mqobsidian    durable memory/context
mq-ums        endpoint/UMS signals
repo-signal   repo quality/readiness
mqlaunch      launcher/menu surface
```

## Development rules

When adding a new command:

1. Add the command implementation.
2. Add or update allowlist/config.
3. Add README command example.
4. Add command docs (`docs/COMMAND_SURFACE.md` + `docs/hal-command-surface.md`).
5. Add tests.
6. Run release checks.

Before PR/release:

```bash
./release-check.sh
mq-hal config-check
```

Do not let model output execute shell directly.

## Recommended next improvement

Add `mqobsidian` context-pack awareness:

```text
mq-hal context status
mq-hal context latest-pack
mq-hal context budget
```

This keeps `mq-hal` aligned with the new MQ-stack direction:

```text
mqobsidian = context compressor
mq-agent = context generator
mq-hal = context operator view
```

## Quick demo script

Run this for a clean demo:

```bash
mq-hal config-check
mq-hal brief
mq-hal stack-status
mq-hal brain health
mq-hal runtime
mq-hal release-brief
mq-hal --explain-intent "visa git status i mq-agent"
```

Good screenshot/demo targets:

```text
mq-hal brief
mq-hal stack-status
mq-hal brain health
mq-hal runtime
mq-hal --explain-intent ...
```

## Definition of done

`mq-hal` is healthy when:

* `mq-hal config-check` passes
* `mq-hal brief` works
* `mq-hal stack-status` reads mq-agent cockpit data or falls back safely
* `mq-hal brain health` sees mqobsidian memory
* `mq-hal runtime` reports Ollama, mq-mcp, GitHub, and brain state
* unsafe commands are refused
* write actions require confirmation
* release checks pass
* docs match command surface
