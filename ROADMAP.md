# mq-hal Roadmap

mq-hal is a local HAL-style command router for the mq ecosystem.

It turns natural-language prompts into structured JSON intents through a local
model, then lets a safe Python router decide what is allowed.

The model never runs shell directly.

```text
user prompt
  ↓
Ollama / Qwen
  ↓
JSON intent
  ↓
safe Python router
  ↓
allowlisted git / repo / mqlaunch / helper actions
```

mq-hal should feel like a local HAL assistant, but behave like a controlled
command router.

In the mq ecosystem, mq-hal is the operator/status layer. It summarizes local
state, diagnostics and readiness. It should not orchestrate mq-agent or own
mq-mcp execution/review logic.

It should be:

- local-first
- explicit
- safe by default
- deterministic when needed
- testable
- mqlaunch-friendly
- repo-aware
- memory-aware
- useful without hiding execution

---

## Current status

Latest stable release:

```text
v0.10.1 — version sync + CI coverage + release-check
```

Completed foundation:

- local natural-language command routing
- Ollama/Qwen intent generation
- JSON intent schema
- safe Python router
- whitelisted command execution
- deterministic no-AI fallback
- repo config
- repo status and CI status
- HAL brief
- HAL release brief
- HAL audit through repo-signal
- HAL stack status
- operator summaries for mqlaunch, repo-signal and mq-mcp-adjacent workflows
- doctor summary
- fix planner
- session memory
- timeline view
- mqlaunch HAL bridge
- README markdown guard
- macOS CI smoke tests
- release-check gate
- GitHub Pages docs

Current recommended next step:

```text
v0.11.0 — intent contract and command-surface hardening
```

---

## Release map

| Version | Theme                                                | Status  |
| ------- | ---------------------------------------------------- | ------- |
| v0.1.x  | Public baseline and local routing foundation         | Done    |
| v0.6.0  | Notifications                                        | Done    |
| v0.8.x  | Doctor summary and fix planner                       | Done    |
| v0.9.x  | Audit, release brief, repo ops, session and timeline | Done    |
| v0.10.0 | HAL Stack Status                                     | Done    |
| v0.10.1 | Version sync, CI coverage and release-check          | Done    |
| v0.11.0 | Intent contract and command-surface hardening        | Next    |
| v0.12.0 | mq-agent and semantic memory integration             | Planned |
| v0.13.0 | Bridget/HAL interaction polish                       | Planned |
| v0.14.0 | Local model backend hardening                        | Planned |
| v0.15.0 | Packaged install and update flow                     | Planned |
| v1.0.0  | Stable local HAL command router                      | Future  |

---

## Completed

### v0.1.x — Public baseline and local routing foundation

Goal:

Create the first local HAL-style router with safe command boundaries.

- [x] Create repository
- [x] Add README
- [x] Add LICENSE
- [x] Add CHANGELOG
- [x] Add VERSION
- [x] Add ROADMAP
- [x] Add GitHub Pages docs
- [x] Add local wrapper command
- [x] Add repo config
- [x] Add initial natural-language routing
- [x] Add Ollama/Qwen model integration
- [x] Add JSON intent output
- [x] Add safe Python router
- [x] Add command allowlist
- [x] Add deterministic fallback path
- [x] Add initial tests and smoke checks

---

### v0.6.0 — Notifications

Goal:

Make longer-running local commands easier to notice.

- [x] Add macOS desktop notification support
- [x] Use `osascript` for local notifications
- [x] Keep notification behavior local
- [x] Avoid notification dependency for core routing

---

### v0.8.x — Doctor summary and fix planner

Goal:

Turn local system health output into safe, readable HAL summaries.

- [x] Add `mq-hal doctor-summary`
- [x] Add `mq-hal doctor-summary --json`
- [x] Add `mq-hal doctor-summary --no-ai`
- [x] Parse `mqlaunch doctor --json`
- [x] Summarize doctor output with Ollama when available
- [x] Fall back to deterministic local summaries
- [x] Add `mq-hal fix-doctor`
- [x] Add `mq-hal fix-doctor --json`
- [x] Add `mq-hal fix-doctor --no-ai`
- [x] Print copy-paste repair plans
- [x] Execute nothing from fix planner automatically

---

### v0.9.x — Audit, release brief, repo ops, session and timeline

Goal:

Make mq-hal useful for real repo/release operations while staying safe.

- [x] Add `mq-hal audit`
- [x] Add `mq-hal audit --json`
- [x] Add repo-signal publish quality check
- [x] Add repo-signal README score check
- [x] Add `mq-hal release-brief`
- [x] Add `mq-hal release-brief --json`
- [x] Check VERSION
- [x] Check CHANGELOG entry
- [x] Check README version badge/reference
- [x] Check git clean/dirty state
- [x] Check recent CI status
- [x] Check latest GitHub release
- [x] Check doctor summary
- [x] Check release-check status
- [x] Add `mq-hal repo-status`
- [x] Add `mq-hal ci`
- [x] Add `mq-hal session`
- [x] Add `mq-hal last`
- [x] Add `mq-hal remember`
- [x] Add local session memory in `~/.mq-hal/session.jsonl`
- [x] Add `mq-hal timeline`
- [x] Add timeline filters
- [x] Add timeline JSON output
- [x] Add README markdown guard
- [x] Add smoke tests for HAL commands

---

### v0.10.0 — HAL Stack Status

Goal:

Show the local mq/HAL toolchain state in one read-only command.

- [x] Add `mq-hal stack-status`
- [x] Add `mq-hal stack-status --json`
- [x] Add `mq-hal stack-status --sample`
- [x] Check mq-hal wrapper
- [x] Check mqlaunch availability
- [x] Check repo-signal availability
- [x] Check optional Bridget availability
- [x] Check configured repo paths
- [x] Check git branch and dirty state
- [x] Check VERSION file
- [x] Check repo-signal publish checklist when available
- [x] Add `tests/stack-status-smoke.sh`
- [x] Document Stack Status in README
- [x] Document Stack Status in command surface docs

---

### v0.10.1 — Version sync, CI coverage and release-check

Goal:

Make release readiness verifiable before adding more HAL features.

- [x] Sync GitHub Pages version with VERSION
- [x] Add HAL router smoke test to CI
- [x] Add Proof section to README
- [x] Add `release-check.sh`
- [x] Check Python syntax
- [x] Check markdown guard
- [x] Check version sync
- [x] Check smoke tests
- [x] Extend docs smoke test
- [x] Verify `docs/index.html` version matches VERSION
- [x] Run CI on `macos-latest`
- [x] Verify smoke tests natively on macOS

---

## Next: v0.11.0 — Intent contract and command-surface hardening

Goal:

Make mq-hal's routed command surface explicit, testable and stable enough for
mqlaunch, mq-agent and future HAL workflows to depend on.

This release should reduce ambiguity.

The model should return a structured intent. The router should validate it. The
docs should describe it. The tests should prove it.

### Scope

- [ ] Add `docs/INTENT_CONTRACT.md`
- [ ] Add `docs/COMMAND_SURFACE.md` or refresh existing command surface docs
- [ ] Define canonical intent schema version
- [ ] Add intent version field
- [ ] Document every intent type
- [ ] Document every allowed action
- [ ] Document required fields per intent
- [ ] Document optional fields per intent
- [ ] Document rejected/unknown intent behavior
- [ ] Document no-AI deterministic fallback behavior
- [ ] Add examples of valid intents
- [ ] Add examples of rejected intents
- [ ] Add command-count guard
- [ ] Add intent-schema smoke test
- [ ] Add router allowlist smoke test
- [ ] Add docs consistency check for command surface
- [ ] Add release-check section for intent contract
- [ ] Update README with intent contract proof
- [ ] Update GitHub Pages with v0.11.0 status

### Proposed intent schema

```json
{
  "schema_version": "1",
  "action": "repo_status",
  "repo": "macos-scripts",
  "path": null,
  "args": {},
  "requires_confirmation": false,
  "safety_class": "read-only"
}
```

### Proposed safety classes

```text
read-only
repo-read
repo-search
repo-write-preview
mqlaunch-allowlisted
doctor-summary
fix-plan-only
session-write
notification
unknown
rejected
```

### Commands to verify

```bash
mq-hal --raw-intent "visa git status i macos-scripts"
mq-hal --explain-intent "hitta OLLAMA_MODEL i mq-hal"
mq-hal --confirm "kör tester i mq-hal"
mq-hal repo-status --json
mq-hal ci --json
mq-hal brief --json
mq-hal release-brief --json
mq-hal audit --json
mq-hal stack-status --json
```

### Definition of done

- [ ] Intent schema is documented
- [ ] Intent schema has a version field
- [ ] Unknown intents are refused
- [ ] Unsafe intents are refused
- [ ] All allowed actions are documented
- [ ] All mqlaunch delegated commands are documented
- [ ] Command-surface docs match README
- [ ] Intent examples are tested
- [ ] Router smoke tests pass
- [ ] Docs smoke tests pass
- [ ] `release-check.sh` passes
- [ ] GitHub Actions pass
- [ ] GitHub release `v0.11.0` exists

---

## v0.12.0 — mq-agent and semantic memory integration

Goal:

Make mq-hal a stronger reasoning/status layer for mq-agent and semantic repo
memory workflows.

Boundary:

```text
mq-hal summarizes status.
mq-agent orchestrates.
mq-mcp executes, reviews and owns memory/reasoning runtime.
```

### Planned scope

- [ ] Add `mq-hal memory-status`
- [ ] Add `mq-hal memory-brief`
- [ ] Add `mq-hal agent-brief`
- [ ] Summarize mq-agent memory status
- [ ] Summarize repo-signal semantic upload state
- [ ] Include semantic memory state in `mq-hal brief`
- [ ] Include semantic memory state in `mq-hal release-brief`
- [ ] Add mq-agent status to `mq-hal stack-status`
- [ ] Add mq-mcp runtime health, vector health and model health to stack summaries
- [ ] Add docs for mq-agent integration
- [ ] Add smoke test for mq-hal → mq-agent
- [ ] Add smoke test for mqlaunch → mq-hal → mq-agent
- [ ] Add fallback behavior if mq-agent is missing

### Boundary rules

- mq-hal may display mq-agent availability and mq-mcp health in summaries
- mq-hal may call read-only status/report commands
- mq-hal must not route review execution around mq-agent
- mq-hal must not implement mq-mcp review, risk or semantic-memory logic

### Possible commands

```bash
mq-hal memory-status
mq-hal memory-brief
mq-hal agent-brief
mq-hal stack-status --include-agent
```

### Example target flow

```text
mqlaunch
  ↓
mq-hal
  ↓
mq-agent
  ↓
repo-signal semantic memory
```

### Non-goals

- No silent memory upload
- No hidden OpenAI API calls
- No destructive agent actions
- No automatic repo mutation

---

## v0.13.0 — Bridget/HAL interaction polish

Goal:

Make the HAL experience feel clearer, more memorable and easier to use without
weakening the safety model.

### Planned scope

- [ ] Improve Bridget/HAL identity docs
- [ ] Add optional HAL greeting/status screen
- [ ] Add clearer terminal output sections
- [ ] Add compact and verbose output modes
- [ ] Add better timeline formatting
- [ ] Add better session summaries
- [ ] Add optional voice-mode design doc
- [ ] Add toggle design for Bridget voice
- [ ] Add local-only voice safety notes
- [ ] Add screenshot or terminal demo

### Possible commands

```bash
mq-hal hello
mq-hal status-screen
mq-hal timeline --compact
mq-hal timeline --details
```

### Non-goals

- No cloud voice dependency by default
- No hidden recording
- No always-on listener
- No voice command execution without confirmation

---

## v0.14.0 — Local model backend hardening

Goal:

Make local model behavior more robust and easier to debug.

### Planned scope

- [ ] Add model availability check
- [ ] Add model latency measurement
- [ ] Add model response validation
- [ ] Add better fallback to deterministic routing
- [ ] Add support notes for Ollama models
- [ ] Add optional LM Studio design notes
- [ ] Add optional llama.cpp design notes
- [ ] Add prompt regression tests
- [ ] Add invalid JSON recovery tests
- [ ] Add model config docs

### Possible commands

```bash
mq-hal model-status
mq-hal model-test
mq-hal --no-ai "visa git status i mq-hal"
mq-hal --raw-intent "visa git status i mq-hal"
```

### Safety requirements

- Invalid model output must not execute
- Non-JSON model output must be rejected or repaired safely
- Unknown actions must be refused
- Model choice must not bypass router safety

---

## v0.15.0 — Packaged install and update flow

Goal:

Make mq-hal easier to install and maintain on a new macOS machine.

### Planned scope

- [ ] Add install script
- [ ] Add uninstall script
- [ ] Add upgrade script
- [ ] Add shell completion notes
- [ ] Add PATH setup docs
- [ ] Add `mq-hal doctor`
- [ ] Add `mq-hal version`
- [ ] Add config validation command
- [ ] Add clean reinstall docs
- [ ] Add optional Homebrew formula plan

### Possible commands

```bash
mq-hal version
mq-hal doctor
mq-hal config-check
mq-hal update
```

### Non-goals

- No hidden daemon
- No automatic startup without user choice
- No silent model download
- No credential handling

---

## v1.0.0 — Stable local HAL command router

Goal:

Make mq-hal stable enough to be the default local HAL command router for the mq
ecosystem.

### v1.0.0 requirements

- [ ] Stable CLI command surface
- [ ] Stable intent schema
- [ ] Stable router allowlist
- [ ] Stable repo config format
- [ ] Stable session memory format
- [ ] Stable timeline output
- [ ] Stable mqlaunch integration
- [ ] Stable mq-agent integration
- [ ] Stable model fallback behavior
- [ ] Complete command docs
- [ ] Complete safety docs
- [ ] Complete troubleshooting docs
- [ ] Complete smoke tests
- [ ] Complete release-check
- [ ] Green CI
- [ ] Protected main branch
- [ ] GitHub release
- [ ] GitHub Pages documentation
- [ ] No known critical safety gaps

---

## Future: Runtime observability layer

Goal:

Keep mq-hal focused on runtime health, diagnostics and operator summaries for
the mq ecosystem.

This layer should make the stack easier to inspect without becoming the
orchestrator.

### Planned scope

- [ ] Add mq-mcp runtime health summary
- [ ] Add vector-store health summary
- [ ] Add model availability and latency summary
- [ ] Add tool availability diagnostics across mqlaunch, mq-agent, mq-mcp and
  repo-signal
- [ ] Add environment-state report with secret redaction
- [ ] Add degraded-mode recommendations without executing fixes automatically

### Non-goals

- No cognition engine
- No review logic
- No direct shell execution from model output

---

## Long-term ideas

These are intentionally not scheduled yet.

- HAL local web dashboard
- richer terminal UI
- Bridget voice mode
- HAL visual timeline
- repo health history
- cross-repo release dashboard
- multi-repo morning brief
- semantic memory comparison between releases
- local model benchmark mode
- safe plugin system
- team-shared repo config
- integration with mq-ums
- integration with mq-mcp safety map
- integration with repo-signal semantic memory
- integration with macos-scripts release-check
- generated architecture diagrams
- demo videos or GIFs

---

## Design principles

mq-hal should remain:

- local-first
- explicit
- safe by default
- command-router oriented
- deterministic when needed
- JSON-intent based
- allowlist enforced
- mqlaunch-friendly
- repo-aware
- memory-aware
- easy to inspect
- easy to disable
- useful without hidden automation

HAL should assist the operator.

HAL should not become an unrestricted shell.

---

## Safety principles

mq-hal must never:

- let the model run shell directly
- execute unknown intents
- execute unsafe commands without confirmation
- mutate repositories invisibly
- upload memory silently
- hide command routing
- ignore repo boundaries
- print secrets in logs
- treat AI output as automatically trusted

Every powerful feature must have:

- dry-run or preview behavior
- explicit confirmation when needed
- documented intent shape
- documented safety class
- tests
- fallback behavior
- failure behavior

---

## Current recommended next step

Work on:

```text
v0.11.0 — intent contract and command-surface hardening
```

This release should make mq-hal easier for mqlaunch, mq-agent and future HAL
features to trust.

---

## HAL Contract + Router Safety Governance

Goal: make `mq-hal` a reliable, verifiable control layer in the MQ ecosystem without role drift into `mq-mcp`, `mq-agent`, or `repo-signal`.

The most important constraint in this repo is already correct:

```text
AI may propose intent.
The router decides what is allowed.
```

The next risk is that constraint eroding as more commands are added.

**Guiding principles**

```text
1. The allowlist is the safety boundary — never bypass it.
2. Every new command must answer: is this HAL's responsibility?
3. Intent schema is a contract — unknown intents must be rejected.
4. Command surface must be machine-readable, not just documented in README.
5. Release may not happen if VERSION, README, CHANGELOG, and CI are out of sync.
6. HAL summarizes and plans — it does not replace mqlaunch, repo-signal, or mq-mcp.
7. Router safety tests must cover unknown intents, unsafe commands, and path escapes.
```

---

## Phase 1 — Branch protection + version signal sync

Goal: close the simplest open gaps before adding anything new.

**Tasks**

- [ ] Enable GitHub branch protection on `main`: require CI success, block force push, require PR for direct pushes.
- [ ] Verify `VERSION` matches the latest release.
- [ ] Verify README version badge matches `VERSION`.
- [ ] Verify `CHANGELOG.md` has an entry for the current version.
- [ ] Verify GitHub release tag matches current version.
- [ ] Review the open pull request — merge or close before next release.

**Definition of done**

- [ ] `main` is protected.
- [ ] README, VERSION, CHANGELOG, and GitHub release all show the same version.
- [ ] No stale open PRs blocking the release line.

---

## Phase 2 — Intent schema contract

Goal: make the JSON intent format a documented, validated contract.

**Tasks**

- [ ] Document all valid intent types in `docs/intent-schema.md`.
- [ ] Add a schema file (`docs/intent_schema.json` or inline in code).
- [ ] Validate that unknown intents are rejected by the router (not silently ignored).
- [ ] Add tests: known intent accepted, unknown intent rejected, malformed JSON rejected.

**Definition of done**

- [ ] Intent schema is documented and machine-readable.
- [ ] Unknown intents fail with a clear error, not a silent no-op.
- [ ] Tests cover schema boundaries.

---

## Phase 3 — Command surface registry

Goal: make the HAL command surface machine-readable so docs, checks, and tests can be generated from a single source.

**New file:** `hal/command_registry.py` or `docs/commands.json`

Each command must declare:

```python
{
    "name": "brief",
    "description": "Short status summary of the current repo",
    "uses_ai": True,
    "uses_network": False,
    "writes_files": False,
    "requires_confirm": False,
    "mqlaunch_alias": "hal brief",
}
```

**Definition of done**

- [ ] All HAL commands are in the registry.
- [ ] README command list can be validated against the registry.
- [ ] `check-command-docs.sh` fails if a command is undocumented.

---

## Phase 4 — Router safety tests

Goal: make the allowlist boundary testable and regression-proof.

**New file:** `tests/test_router_safety.py`

**Required tests**

- [ ] Unknown intent is rejected.
- [ ] Unsafe shell command is not executed.
- [ ] Repo path escape (e.g. `../../etc/passwd`) is blocked.
- [ ] `--confirm` flag is respected for write actions.
- [ ] `--no-ai` flag bypasses the model but still hits the router.
- [ ] Empty intent payload is rejected.
- [ ] Valid intent for each command type is accepted.

**Definition of done**

- [ ] All router safety tests pass in CI.
- [ ] No new command can be added without a corresponding test.

---

## Phase 5 — Integration boundary

Goal: make the role of `mq-hal` explicit relative to the other MQ repos so future commands are added to the right place.

**Files to update:** `docs/integration.md`, `README.md`

**Role division**

| Repo          | Role                                                       |
| ------------- | ---------------------------------------------------------- |
| `mq-hal`      | interprets natural language, produces status and safe plans |
| `mqlaunch`    | command surface, menu, terminal entrypoint                 |
| `repo-signal` | repo quality and publish readiness checks                  |
| `mq-mcp`      | MCP tool surface and local tool execution                  |
| `mq-agent`    | larger orchestration and agent flows                       |

Every proposed new HAL command must answer:

```text
Is this HAL's responsibility, or does it belong in mqlaunch, repo-signal, mq-mcp, or mq-agent?
```

**Definition of done**

- [ ] `docs/integration.md` describes the boundary clearly.
- [ ] README answers: what does `mq-hal` do, what does it not do?
- [ ] The boundary is referenced in the command registry.

---

## Phase 6 — Release gate v2

Goal: make release a system check, not just a version bump.

**Files to update:** `scripts/release-check.sh`, `scripts/validate.sh`

**Release must be blocked if**

- [ ] `VERSION` does not match the latest CHANGELOG entry.
- [ ] README badge is wrong.
- [ ] CHANGELOG is missing the version.
- [ ] GitHub release tag is missing.
- [ ] CI is red.
- [ ] Any undocumented command exists in the registry.
- [ ] Any router safety test fails.

**Definition of done**

- [ ] `scripts/release-check.sh` runs all checks automatically.
- [ ] Release output clearly shows what was verified.
- [ ] Release can be run with `--dry-run`.

---

**Priorities**

Do first: branch protection → version signal sync → resolve open PR → intent schema contract → router safety tests.

Do next: command surface registry → integration boundary docs → release gate v2.

Defer: more HAL commands, Ollama model tuning, deeper mq-agent integration, voice/TTS output — until the above is stable.

---

This repo is in good shape because the core constraint is right. The next work is not more commands — it is making the existing boundary stronger, documented, and testable.
