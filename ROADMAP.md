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
v2.3.0 — Local-First Model Routing Control Room
```

Completed foundation:

- local natural-language command routing
- Ollama/Qwen intent generation + model profiles
- JSON intent schema (v1, formally validated)
- safe Python router + intent allowlist
- whitelisted command execution
- deterministic no-AI fallback
- repo config
- repo status and CI status
- HAL brief, release brief, audit
- HAL stack status + mq-agent integration
- doctor summary and fix planner
- session memory and timeline
- mqlaunch HAL bridge
- README markdown guard + release-check gate
- GitHub Pages docs
- Advanced Ollama Runtime: plan, critic, execute, tools, models
- Visual HAL: analyze-diagram, review-ui, architecture-brief
- Packaged install/update flow + release gate v2
- Learn layer with secret redaction
- Stack / Brain / Release / Runtime control centers (v1.3–v1.6)
- TUI dashboard, timeline & history, operator actions (v1.7–v1.9)
- HAL Operator Platform — unified `mq-hal` dashboard over the whole stack (v2.0)
- Context Pack Status — read-only mqobsidian token-reduction visibility (v2.1)
- Operator Feedback Polish — explicit dashboard and action outcomes (v2.2)
- Local-First Model Routing Control Room — advisory routing visibility (v2.3)

Current recommended next step:

```text
Maintenance — keep routing advisory until a fresh evidence set passes the gate
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
| v0.11.0 | Intent contract and command-surface hardening        | Done    |
| v0.12.0 | mq-agent and semantic memory integration             | Done    |
| v0.13.0 | Bridget/HAL interaction polish                       | Done    |
| v0.14.0 | Advanced Ollama Runtime                              | Done    |
| v0.14.5 | Visual HAL                                           | Done    |
| v0.15.x | Packaged install, update flow and release gate v2    | Done    |
| v1.0.0  | Stable local HAL command router                      | Done    |
| v1.0.1  | HAL Learn Layer                                      | Done    |
| v1.0.2  | Runtime observability: env-status                    | Done    |
| v1.0.3  | ROADMAP cleanup — all stale items resolved           | Done    |
| v1.1.0  | mq-mcp runtime health observability in stack-status  | Done    |
| v1.2.0  | Vector-store health summary in stack-status          | Done    |
| v1.3.0  | Stack Operator Foundation                            | Done    |
| v1.4.0  | Brain Control Center                                 | Done    |
| v1.5.0  | Release Control Center                               | Done    |
| v1.6.0  | Runtime Control                                      | Done    |
| v1.7.0  | TUI Dashboard                                        | Done    |
| v1.8.0  | Timeline and History                                 | Done    |
| v1.9.0  | Operator Actions                                     | Done    |
| v2.0.0  | HAL Operator Platform                                | Done    |
| v2.1.0  | Context Pack Status                                  | Done    |
| v2.1.1  | Stack-loop history compatibility                     | Done    |
| v2.2.0  | Operator feedback polish                             | Done    |
| v2.3.0  | Local-First Model Routing Control Room               | Done    |

---

## Operator Goal

Build `mq-hal` into the **operator layer for the full MQ stack**.

Role:

```text
mqlaunch → start
mq-agent → orchestration
mq-mcp → runtime / review
repo-signal → scoring
mqobsidian → memory
mq-hal → operator control room
```

Principle:

**mq-hal should not think, review or store. It should only read, summarize,
display and route.**

---

## v1.3.0 — Stack Operator Foundation (1–2 weeks)

### Goal

Show the whole stack status from one command.

### Build

```bash
mq-hal stack
```

Output:

```text
MQ Stack

mq-agent        PASS
mq-mcp          PASS
repo-signal     PASS
mqobsidian      WARN
brain           PASS

Overall:
92/100
```

### Add

```bash
mq-hal stack --json
mq-hal status
mq-hal doctor
```

### Input

Read from:

```text
mq-agent stack cockpit --json
```

### Deliverables

```text
hal/
  stack.py
  status.py
  doctor.py
```

### Definition of Done

- [x] stack status works
- [x] JSON works
- [x] no custom contracts

---

## v1.4.0 — Brain Control Center (1 week)

### Goal

Make mqobsidian visible.

Commands:

```bash
mq-hal brain
mq-hal brain health
mq-hal brain recent
mq-hal brain search
```

Show:

```text
brain notes
truth exports
learn exports
review exports
```

### Folders

```text
memory/
learn/
truth/
reviews/
```

### Output

```text
Recent notes
Recent reviews
Latest release
```

### Done

- [x] brain status
- [x] brain search
- [x] latest exports

---

## v1.5.0 — Release Control Center (1 week)

### Goal

Central release overview.

Commands:

```bash
mq-hal release
mq-hal release gates
mq-hal release blockers
```

Show:

```text
Repo
Version
Ready
Blockers
```

### Read From

```bash
mq-agent stack release-check --json
```

### Done

- [x] blocker list
- [x] release score

---

## v1.6.0 — Runtime Control (1 week)

### Goal

Show local services.

Commands:

```bash
mq-hal runtime
mq-hal runtime services
```

Show:

```text
Ollama
mq-mcp
GitHub
brain
```

### Status

```text
RUNNING
WARN
DOWN
```

### Done

- [x] runtime status
- [x] health checks

---

## v1.7.0 — TUI Dashboard (2 weeks)

### Goal

Full terminal dashboard.

Start:

```bash
mq-hal
```

View:

```text
┌──────────────────────┐
Stack
Release
Brain
Runtime
History
Alerts
└──────────────────────┘
```

### Keys

```text
1 Stack
2 Brain
3 Release
4 Runtime
5 History
q Exit
```

### Done

- [x] navigation
- [x] refresh

---

## v1.8.0 — Timeline & History (1 week)

### Goal

Show changes.

Commands:

```bash
mq-hal history
mq-hal alerts
```

Show:

```text
stack score
brain growth
release history
```

### Read From

```text
~/.mq-agent/
mqobsidian/
```

### Done

- [x] trend view
- [x] history

---

## v1.9.0 — Operator Actions (1 week)

### Goal

Make HAL useful.

Commands:

```bash
mq-hal next
mq-hal fix
mq-hal open
```

Example:

```text
BLOCKER:
CHANGELOG missing

Action:
open CHANGELOG.md
```

### Done

- [x] actions
- [x] routing

---

## v2.0.0 — HAL Operator Platform

Status: Done — `mq-hal` with no arguments opens the unified operator dashboard
(stack, brain, release, runtime, history, alerts) over the whole MQ stack.

### Final Goal

```text
start mq-hal

↓

see:
stack
brain
runtime
release
history

↓

choose

↓

mq-agent runs
```

### Directory Structure

```text
mq-hal/
├── hal/
│   ├── stack/
│   ├── release/
│   ├── runtime/
│   ├── brain/
│   ├── dashboard/
│   ├── history/
│   └── operator/
├── docs/
├── tests/
├── assets/
└── ROADMAP.md
```

### Priority Build Order

```text
v1.3 Stack
v1.4 Brain
v1.5 Release
v1.6 Runtime
v1.7 Dashboard
v1.8 History
v1.9 Actions
v2.0 Operator Platform
```

### Definition of Done

When you can open:

```bash
mq-hal
```

and understand the whole MQ ecosystem's status without opening a single repo.

---

## v2.1.0 — Context Pack Status

Status: Done — `mq-hal context` shows read-only mqobsidian context-pack
readiness from the operator layer.

### Goal

Make the token-reduction layer visible without moving generation or storage
ownership into `mq-hal`.

```text
mqobsidian -> stores schemas, templates, examples and task packs
mq-agent   -> generates context packs
mq-hal     -> shows context status and routes the operator
```

### Build

```bash
mq-hal context
mq-hal context status
mq-hal context latest-pack
mq-hal context budget
mq-hal context open
mq-hal context --json
```

### Definition of Done

- [x] Context scaffold checks are read-only.
- [x] Missing mqobsidian returns WARN, not FAIL.
- [x] Latest task pack and target readiness are visible.
- [x] Token budget delegates to mqobsidian on demand.
- [x] Dashboard includes a Context panel.
- [x] README, command docs, guide and release-check cover the command.

---

## v2.2.0 — Operator Feedback Polish

Status: Done — the main operator surfaces share a versioned feedback contract.

### Goal

Standardize operator feedback before v2.3 adds more routing decisions to
explain. Main surfaces are `stack`, `release`, `runtime`, `brain`, `context`,
`dashboard`, `next`, `open`, and `fix`.

### Step 1 — Unified status levels

All main HAL surfaces use `PASS`, `WARN`, `FAIL`, `SKIPPED`, or `UNAVAILABLE`.
Legacy input values are normalized at the presentation boundary.

### Step 2 — Explanatory results

Warnings and failures expose what happened, why it matters, evidence, the next
action, and a suggested command through `mq.feedback.v1`.

### Step 3 — Unified `next_action`

Actionable JSON results return `text`, `command`, `safety`, and
`requires_confirmation`. HAL displays this metadata but never executes it
automatically.

### Step 4 — Confirmation feedback

Operator previews show the exact command, affected repo or owner, safety class,
expected effect, cancellation path, and delegated exit status.

### Step 5 — Surface parity

CLI, JSON, dashboard panels, `mqlaunch hal`, and MCP consumers receive the same
semantic status and advisory action metadata from the underlying command.

### Step 6 — Negative tests

Contract and smoke tests cover unavailable dependencies, malformed feedback,
omitted actions for healthy results, confirmation requirements, cancellation,
delegated exit codes, and human/JSON status parity.

### Definition of Done

- [x] A shared feedback model exists.
- [x] All main commands use the same status levels.
- [x] Warnings and errors contain a concrete next action.
- [x] Suggested commands carry safety metadata.
- [x] No action runs implicitly from feedback.
- [x] CLI, JSON, and TUI are semantically consistent.
- [x] Delegated exit codes are preserved.
- [x] Negative tests cover failure, cancellation, and degraded modes.
- [x] README, command surface, and guide are updated.

---

## v2.3.0 — Local-First Model Routing Control Room

Status: Done — Phases 0–5, durable outcome storage, per-decision history, and
the evidence review are delivered. `mq-agent route history` is the
authoritative producer;
`mq-hal route history` and `route explain <decision-id>` read it and degrade to
WARN only when mq-agent does not serve the contract or nothing matches.

The evidence gate has been run and returned `NOT_ELIGIBLE`. One gate fails,
`verification-success-rate`, and it is a local-model capability limit rather
than a missing-evidence problem. PR 8 is closed on that verdict: the gate
works, the model does not reach it. Automatic routing stays disabled and
`diff-summary` stays in shadow mode. See "Evidence review" below.

### Goal

Make local-first model routing visible and understandable from the HAL operator
layer without moving routing, execution, review or memory ownership into
`mq-hal`.

The initiative should answer four operator questions:

```text
Which model path is recommended for this task?
Why was that path selected?
Did the local Ollama candidate pass verification?
When should the task be escalated to Codex or Claude?
```

The first release is advisory and read-only.

It must not automatically replace Codex or Claude, intercept IDE prompts or
execute model-generated commands.

### User value

The MQ stack already uses Ollama for local intent generation, model runtime
inspection, learn extraction and local vision.

The missing capability is a shared, evidence-based decision layer that knows
when local Ollama is sufficient and when a stronger coding agent is required.

Expected benefits:

- use Ollama for proven low-risk tasks
- reserve Codex and Claude for complex or high-risk work
- reduce unnecessary cloud context and model calls
- provide the same MQ context to Codex and Claude in VS Code
- measure local model quality instead of assuming it
- make every routing and escalation decision visible to the operator

### Architecture boundary

```text
VS Code / mqlaunch
        |
        v
Codex or Claude
        |
        v
mq-mcp MCP tools
        |
        v
mq-agent model router
        |
        +----> local Ollama candidate
        |
        +----> Codex / Claude escalation recommendation
        |
        v
deterministic verification
        |
        v
mqobsidian verified outcome
        |
        v
mq-hal status and explanation
```

Ownership remains:

| Repository      | Responsibility                                                 |
| --------------- | -------------------------------------------------------------- |
| `mq-agent`      | Task classification, routing policy, confidence and escalation |
| `mq-mcp`        | MCP tools, safety contracts and deterministic verification     |
| `mqobsidian`    | Verified routing outcomes and historical evidence              |
| `repo-signal`   | Repository and change-risk signals                             |
| `mq-hal`        | Read-only status, explanation and operator navigation          |
| `macos-scripts` | Thin `mqlaunch` terminal entrypoint                            |
| Codex / Claude  | Authoritative coding and architecture agents                   |
| Ollama          | Advisory local candidate for approved task classes             |

Boundary rules:

- `mq-hal` must not calculate the authoritative routing decision.
- `mq-hal` must not execute Ollama candidates.
- `mq-hal` must not store routing history.
- `mq-hal` reads structured state from `mq-agent`.
- `mq-hal` explains the decision and routes the operator.
- Ollama output is evidence to verify, never authority.
- Codex and Claude remain authoritative for medium/high-risk work.

### Program phases

#### Phase 0 — Define the routing contract in mq-agent

Owner: `mq-agent`

Create versioned schemas for routing decisions and verified outcomes.

Proposed schemas:

```text
schemas/model_route_decision.schema.json
schemas/model_route_outcome.schema.json
```

Minimum decision fields:

```json
{
  "schema": "mq.model-route-decision.v1",
  "task_class": "diff-summary",
  "risk": "low",
  "recommended_route": "local-shadow",
  "local_model": "qwen3:4b-instruct",
  "authoritative_agent": "codex",
  "reason_codes": [
    "read-only",
    "deterministic-verification-available"
  ],
  "escalation_conditions": [
    "schema-invalid",
    "verification-failed",
    "confidence-below-threshold"
  ]
}
```

Instructions:

1. Define a closed set of task classes.
2. Define a closed set of risk levels.
3. Use machine-readable reason codes, not only explanatory prose.
4. Require an explicit authoritative agent.
5. Require explicit escalation conditions.
6. Reject unknown enum values.
7. Keep routing inspection read-only.

Definition of Done:

- [x] Decision and outcome schemas are versioned.
- [x] Invalid task classes and routes are rejected.
- [x] Every decision names its reason and escalation conditions.
- [x] No model call is required to validate the contract.
- [x] Unit tests cover valid and malformed decisions.

#### Phase 1 — Build shadow routing in mq-agent

Owner: `mq-agent`

Proposed commands:

```bash
mq-agent route inspect "<task>"
mq-agent route shadow "<task>"
mq-agent route report
```

Behavior:

```text
route inspect
  -> classify task and risk
  -> recommend a route
  -> make no model call
  -> write nothing

route shadow
  -> create an Ollama candidate
  -> preserve Codex or Claude as authoritative
  -> verify the candidate where deterministic checks exist
  -> return a comparison record

route report
  -> aggregate verified outcomes
  -> show where Ollama is reliable
  -> show where escalation remains required
```

Initial local task candidates:

- diff summarization
- documentation review
- repository-health summarization
- test-area suggestions
- review-finding classification
- context-pack summarization

Initial cloud-required task classes:

- cross-repository architecture
- security-critical review
- destructive operations
- release decisions
- schema or contract migration
- changes without deterministic verification

Definition of Done:

- [x] Inspect mode performs no model call and no write.
- [x] Shadow mode cannot replace the authoritative agent.
- [x] Missing Ollama returns a structured degraded result.
- [x] Failed or malformed Ollama output causes escalation.
- [x] Routing reports distinguish attempted, verified and accepted outcomes.
- [x] No automatic execution exists.

#### Phase 2 — Expose the router through mq-mcp

Owner: `mq-mcp`

Proposed read-only MCP tools:

```text
mq_route_inspect
mq_route_shadow
mq_context_pack
mq_route_verify
mq_route_report
```

Tool responsibilities:

| Tool               | Responsibility                               |
| ------------------ | -------------------------------------------- |
| `mq_route_inspect` | Return the structured routing recommendation |
| `mq_route_shadow`  | Request a local candidate without mutation   |
| `mq_context_pack`  | Return task-scoped MQ context                |
| `mq_route_verify`  | Run deterministic checks against a candidate |
| `mq_route_report`  | Return aggregated verified routing evidence  |

Safety requirements:

- All first-release tools are read-only.
- Model output is treated as untrusted input.
- Tools return versioned structured output.
- No tool executes model-produced shell commands.
- No tool writes to a repository.
- No tool stores an outcome before verification.
- Missing dependencies degrade gracefully.
- Secrets and environment values are redacted.

Definition of Done:

- [x] Every tool is classified in the mq-mcp safety map.
- [x] Input and output schemas are validated.
- [x] Ollama failures return structured unavailable results.
- [x] Contract tests pass without a running Ollama server.
- [x] Live Ollama tests remain optional.
- [x] Codex and Claude can call the same MCP tools.

#### Phase 3 — Integrate with Codex and Claude in VS Code

Owners: `mq-mcp`, repository maintainers

Both coding agents should use the same MCP server and the same routing
contracts.

Repository instructions:

```text
AGENTS.md  -> Codex instructions
CLAUDE.md  -> Claude Code instructions
```

Recommended instruction:

```md
## MQ model routing

Before planning a non-trivial change:

1. Call `mq_route_inspect`.
2. Load `mq_context_pack` for cross-repository work.
3. Use `mq_route_shadow` only as advisory evidence.
4. Treat Codex or Claude as authoritative for medium/high-risk work.
5. Verify local findings against repository code and tests.
6. Escalate when the router reports an escalation condition.
```

Expected VS Code flow:

```text
operator describes task
  -> Codex or Claude calls mq_route_inspect
  -> agent loads task-specific context
  -> optional local Ollama shadow candidate
  -> agent performs authoritative work
  -> deterministic verification
  -> verified outcome becomes eligible for history
```

Non-goals:

- Do not replace the Codex or Claude model backend.
- Do not route Claude through a non-Claude LLM gateway.
- Do not intercept every editor prompt.
- Do not require the operator to leave VS Code.
- Do not create separate routing implementations for each agent.

Definition of Done:

- [x] Codex can discover and call the routing tools.
- [x] Claude Code can discover and call the same tools.
- [x] Both agents receive equivalent structured context.
- [x] Repository instructions describe advisory versus authoritative output.
- [x] A documented example covers one Codex and one Claude workflow.

#### Phase 4 — Add the mq-hal operator surface

Owner: `mq-hal`

`mq-hal` exposes routing state but delegates all authoritative data to
`mq-agent`.

Proposed commands:

```bash
mq-hal route
mq-hal route status
mq-hal route inspect "<task>"
mq-hal route history
mq-hal route accuracy
mq-hal route explain <decision-id>
mq-hal route --json
```

Expected status:

```text
MQ Model Routing

Router:              PASS
Mode:                SHADOW
Ollama:              PASS
Local model:         qwen3:4b-instruct
Authoritative agent: Codex / Claude

Verified outcomes:   38
Local accepted:      29
Escalated:            9

Reliable local task classes:
  diff-summary        96%
  docs-review         94%
  repo-health         91%

Cloud-required:
  architecture
  security-review
  cross-repo-change

Next:
  mq-hal route explain latest
```

Implementation rules:

1. Read structured JSON from `mq-agent route`.
2. Do not duplicate routing thresholds in `mq-hal`.
3. Do not calculate accuracy from unverified attempts.
4. Display reason codes in operator-friendly language.
5. Make local, shadow and escalated states visually distinct.
6. Preserve `--json` parity with human output.
7. Missing `mq-agent` or Ollama should produce WARN, not a crash.
8. Never present a shadow candidate as an approved result.

Possible intent additions:

```text
model_route_status
model_route_inspect
model_route_history
model_route_accuracy
model_route_explain
```

Each new intent must be:

- represented in the intent schema
- explicitly allowlisted
- mapped to a read-only handler
- covered by positive and negative routing tests
- documented in the command surface

Definition of Done:

- [x] `mq-hal route` shows mode, health and current model.
- [x] Status is sourced from `mq-agent`, not recomputed.
- [x] Accuracy includes verified outcomes only.
- [x] Escalation reasons are visible.
- [x] `--json` output validates against a schema.
- [x] Dashboard includes a Model Routing panel.
- [x] Unknown route subcommands are rejected.
- [x] Missing router dependencies degrade to WARN.
- [x] README, command docs, guide and release-check cover the surface.

#### Phase 5 — Add the mqlaunch thin entrypoint

Owner: `macos-scripts`

Proposed command:

```bash
mqlaunch route "$@"
```

Required behavior:

```text
mqlaunch route ...
  -> mq-agent route ...
```

Rules:

- No routing logic in shell.
- No local confidence thresholds in the command registry.
- Preserve all arguments and exit codes.
- Classify the command as a `thin-entrypoint`.
- Do not modify `ask`, `fix` or `chat`.
- Add a behavior test proving lossless delegation.

Definition of Done:

- [x] Every argument reaches `mq-agent route` unchanged.
- [x] Exit codes 0, 1, 2 and 127 are preserved.
- [x] Help identifies `mq-agent` as the owner.
- [x] No fallback model call exists in `macos-scripts`.
- [x] The command registry and generated surfaces remain synchronized.

### Evidence gate before automatic routing

Automatic local handling must remain disabled until shadow evidence satisfies a
documented promotion policy.

Minimum evidence proposal:

```text
at least 50 verified outcomes for one task class
at least 90% deterministic verification success
zero unauthorized writes
zero safety-contract violations
all malformed outputs escalated
Ollama-unavailable path proven
manual operator approval to promote the task class
```

Promotion applies to one task class at a time.

Example:

```text
diff-summary:
  shadow -> approved-local

architecture:
  cloud-required -> unchanged
```

A strong result for one task class must never authorize another class.

#### Evidence review — 2026-08-07, diff-summary — closed

PR 8 is closed with the verdict **the gate works, the model does not reach it**.
`diff-summary` stays in shadow mode. No task class has been promoted. Reopen
this only with a different local model and a fresh evidence set; the decision
below is not a backlog item waiting on more runs.

PR 8 was executed once. 130 `route shadow` runs against 129 distinct real
commit diffs from `mq-agent`, `mq-hal`, `mq-mcp`, `repo-signal` and
`macos-scripts`, every run supplying material via `--context-file`, plus one run
against a dead Ollama endpoint to exercise the unavailable path.

```text
mq-agent route evidence-review diff-summary
  local model    qwen3:4b-instruct
  valid outcomes 130      responded 129
  verified        56      distinct verified tasks 56
  grounded        56/56   malformed escalated 1/1
  decision       NOT_ELIGIBLE
  failed gates   verification-success-rate (0.434, requires >= 0.9)
  vacuous gates  zero-unauthorized-writes
```

Eight of nine gates pass. The single blocker is verification success rate, and
it is not a volume problem: more runs reproduce the same rate. `qwen3:4b-instruct`
fails the `evidence-grounded` check introduced in mq-agent #182 on roughly half
of the runs that the model answered.

The cause is fabrication, not a strict comparison. Across 97 evidence entries,
82.5% are verbatim, 2.1% fall below the minimum quote length, and 15.5% are
text that appears nowhere in the material under any normalization. No entry
failed on whitespace differences alone, and none consisted of real lines
stitched out of order. The check is catching invented citations, which is what
it is for.

Because grounding is all-or-nothing across roughly 4.4 entries per run, 82.5%
per entry becomes a 43% run rate. Reaching a 90% run rate would require per
entry accuracy of 0.90 at one citation and 0.98 at five.

Four alternative comparisons were evaluated offline against identical model
output: the current one, splitting entries on line breaks, matching without
whitespace, and both plus diff-marker stripping. All four score 9/22. Three
evidence-count caps were then measured with real calls on the same material:
`maxItems` 1, 2 and 5 give run rates of 0.36, 0.50 and 0.41, and per-entry
accuracy *falls* from 0.83 to 0.70 when the cap drops to 2, because the model
selects longer and less accurate quotes rather than keeping its best ones.

No verification rule or schema constant in `mq-agent` moves the rate near the
gate. This is a capability limit of `qwen3:4b-instruct`. A larger local model
is the only untried path and was not measured, because the host has 5 GiB free.

Lowering the bar was considered and rejected: 15.5% of citations are invented,
so any partial-credit rule would admit fabricated evidence into a promotion
decision. The gate is left exactly as `mq-agent` #182 defined it.

The 130 outcomes remain in the local evidence store as read-only history, per
the rollback rules below. `mq-hal` reports this state; it does not weaken it.

### Security and trust model

Trust order:

```text
repository code and tests
  >
deterministic MQ contracts
  >
verified historical outcomes
  >
Codex / Claude review
  >
Ollama candidate
```

Permanent rules:

- Ollama never approves its own output.
- Confidence text from a model is not a confidence score.
- Verification failure always escalates.
- Missing evidence never becomes implicit approval.
- Routing history must not contain secrets or raw credentials.
- Destructive actions remain outside automatic local routing.
- Release and security decisions require an authoritative agent and operator
  confirmation.
- HAL explains decisions but never weakens them.

### Observability

Track:

```text
task class
selected route
local model
risk level
reason codes
verification result
escalation reason
authoritative agent
accepted or rejected outcome
latency
timestamp
schema version
```

Do not treat these as equivalent:

```text
attempted
model returned output
schema valid
deterministically verified
accepted by authoritative agent
accepted by operator
```

Reports must preserve these distinctions.

### Rollback

Every phase must remain independently removable.

Rollback order:

1. Disable the Model Routing panel in `mq-hal`.
2. Disable MCP routing tools.
3. Disable shadow mode in `mq-agent`.
4. Keep deterministic verification and stored schemas.
5. Preserve historical outcomes as read-only evidence.
6. Fall back to direct Codex and Claude workflows.

The operator must always be able to work normally when Ollama or the router is
unavailable.

### Final Definition of Done

- [x] `mq-agent` owns one versioned routing policy.
- [x] `mq-mcp` exposes validated read-only routing tools.
- [x] Codex and Claude use the same MCP contract in VS Code.
- [x] Ollama runs only as an advisory local candidate.
- [x] `mqobsidian` stores verified outcomes, not raw model claims.
- [x] `repo-signal` supplies risk evidence without owning routing.
- [x] `mq-hal` shows status, reasons, history and escalation.
      `route history` and `route explain <decision-id>` read
      `mq.model-route-history.v1` from mq-agent; HAL stores nothing.
- [x] `mqlaunch` is a lossless thin entrypoint.
- [x] Automatic routing remains disabled until the evidence gate passes.
      Demonstrated 2026-08-07: the gate ran, returned `NOT_ELIGIBLE`, and
      nothing was promoted.
- [x] The full stack works when Ollama is unavailable.
      Verified 2026-08-07 at every layer: `mq-agent route shadow` records a
      structured `model-unavailable` outcome, `mq_route_shadow` propagates it,
      `mqlaunch route` preserves exit codes, and `mq-hal route status`
      degrades to WARN while `history`, `accuracy` and `dashboard` stay PASS.
- [x] No component duplicates another repository's authority.

### Recommended implementation order

```text
PR 1  mq-agent: define route decision and outcome schemas
PR 2  mq-agent: add read-only inspect and shadow mode
PR 3  mq-mcp: expose validated routing MCP tools
PR 4  Codex/Claude: add repository instructions and prove VS Code usage
PR 5  mq-hal: add read-only Model Routing Control Room
PR 6  macos-scripts: add the thin mqlaunch route entrypoint
PR 7  mqobsidian: persist verified routing outcomes
PR 8  evidence review: decide whether one task class may leave shadow mode
```

PR 1-7 are delivered. PR 8 ran on 2026-08-07, returned `NOT_ELIGIBLE` for
`diff-summary`, and is closed: the gate works, the local model does not reach
it. See "Evidence review" above. No task class has left shadow mode.

Do not combine these into one cross-repository PR. Each repository must remain
independently releasable and revertible.

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

## v0.11.0 — Intent contract and command-surface hardening

Goal:

Make mq-hal's routed command surface explicit, testable and stable enough for
mqlaunch, mq-agent and future HAL workflows to depend on.

### Scope

- [x] Add `docs/INTENT_CONTRACT.md`
- [x] Add `docs/COMMAND_SURFACE.md` or refresh existing command surface docs
- [x] Define canonical intent schema version
- [x] Add intent version field
- [x] Document every intent type
- [x] Document every allowed action
- [x] Document required fields per intent
- [x] Document optional fields per intent
- [x] Document rejected/unknown intent behavior
- [x] Document no-AI deterministic fallback behavior
- [x] Add examples of valid intents
- [x] Add examples of rejected intents
- [x] Add command-count guard
- [x] Add intent-schema smoke test
- [x] Add router allowlist smoke test
- [x] Add docs consistency check for command surface
- [x] Add release-check section for intent contract
- [x] Update README with intent contract proof
- [x] Update GitHub Pages with v0.11.0 status

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

### Structured Intent Engine

- [x] Move intent contract to formal JSON Schema
- [x] Add `schemas/intent.schema.json`
- [x] Validate all model output before routing
- [x] Reject malformed intents
- [x] Reject unknown actions
- [x] Add intent risk classification
- [x] Add rollback-plan field
- [x] Add requires-confirmation field
- [x] Add intent contract examples
- [x] Add intent contract tests

### Definition of done

- [x] Intent schema is documented
- [x] Intent schema has a version field
- [x] Unknown intents are refused
- [x] Unsafe intents are refused
- [x] All allowed actions are documented
- [x] All mqlaunch delegated commands are documented
- [x] Command-surface docs match README
- [x] Intent examples are tested
- [x] Router smoke tests pass
- [x] Docs smoke tests pass
- [x] `release-check.sh` passes
- [x] GitHub Actions pass
- [x] GitHub release `v0.11.0` exists

### Carried forward to v0.14.0

These items were not completed and are required before or during v0.14.0:

- [x] GitHub Actions pass on `main`
- [x] Add intent risk classification to intent schema
- [x] Add rollback-plan field to intent schema
- [x] Add requires-confirmation field to intent schema
- [x] No new command merged without a corresponding router test

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

- [x] Add `mq-hal memory-status`
- [x] Add `mq-hal memory-brief`
- [x] Add `mq-hal agent-brief`
- [x] Summarize mq-agent memory status
- [x] Summarize repo-signal semantic upload state
- [x] Include semantic memory state in `mq-hal brief`
- [x] Include semantic memory state in `mq-hal release-brief`
- [x] Add mq-agent status to `mq-hal stack-status`
- [x] Add mq-mcp runtime health, vector health and model health to stack summaries
- [x] Add docs for mq-agent integration
- [x] Add smoke test for mq-hal → mq-agent
- [x] Add smoke test for mqlaunch → mq-hal → mq-agent
- [x] Add fallback behavior if mq-agent is missing

### Boundary rules

- mq-hal may display mq-agent availability and mq-mcp health in summaries
- mq-hal may call read-only status/report commands
- mq-hal must not route review execution around mq-agent
- mq-hal must not implement mq-mcp review, risk or semantic-memory logic

### Repo Memory

- [x] Add repo indexing (`mq-hal index <repo>`)
- [x] Add optional Ollama embeddings support (`mq-hal index <repo> --embeddings`)
- [x] Add memory search
- [x] Add repo-aware retrieval
- [x] Add repo-map generation
- [x] Add architecture knowledge extraction
- [x] Add roadmap knowledge extraction
- [x] Add release-history knowledge extraction

### Possible commands

```bash
mq-hal memory-status
mq-hal memory-brief
mq-hal agent-brief
mq-hal stack-status --include-agent
mq-hal index <repo>
mq-hal search <query>
mq-hal ask-repo <question>
mq-hal repo-map
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

### Carried forward to v0.14.0

- [x] mq-mcp runtime health, vector health and model health in
  `stack-status`
- [x] `mq-hal index <repo>` — local repo indexing
- [x] Ollama embeddings support
- [x] `mq-hal search <query>` — memory search
- [x] `mq-hal ask-repo <question>` — repo-aware retrieval
- [x] `mq-hal repo-map` — repo-map generation
- [x] Architecture, roadmap and release-history knowledge extraction

---

## v0.13.0 — Bridget/HAL interaction polish

Goal:

Make the HAL experience feel clearer, more memorable and easier to use without
weakening the safety model.

### Planned scope

- [x] Improve Bridget/HAL identity docs
- [x] Add optional HAL greeting/status screen
- [x] Add clearer terminal output sections
- [x] Add compact and verbose output modes
- [x] Add better timeline formatting
- [x] Add better session summaries
- [x] Add optional voice-mode design doc
- [x] Add toggle design for Bridget voice
- [x] Add local-only voice safety notes
- [x] Add screenshot or terminal demo

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

### Carried forward to v0.14.0

- [x] Add better session summaries (grouped by type, counts)

### Carried forward to v0.15.0

- [x] Add screenshot or ASCII terminal demo

---

## Before v0.14.0 — Stabilization gate

**Do not add more commands or merge new features until all items below
are satisfied.**

This gate exists because the constraint "AI may propose intent, the router
decides what is allowed" must be verifiably true before the runtime layer
gets more powerful.

### Version sync (satisfied ✓)

- [x] `VERSION` = 0.13.0
- [x] README badge = 0.13.0
- [x] CHANGELOG entry for 0.13.0
- [x] GitHub release `v0.13.0` exists

### Safety infrastructure (satisfied ✓)

- [x] `schemas/intent.schema.json` — formal intent schema
- [x] `tests/intent-schema-smoke.sh` — schema/code parity enforced
- [x] `tests/router-safety-smoke.sh` — allowlist boundary tested
- [x] `docs/COMMAND_SURFACE.md` — canonical command registry
- [x] `tools/check-command-docs.sh` — command docs enforced in release

### Remaining before v0.14.0

- [x] GitHub branch protection on `main`: require CI success,
  block force push
- [x] GitHub Actions green on `main`
- [x] `docs/INTEGRATION.md` integration boundary describes current
  role division clearly
- [x] All carried-forward items from v0.11.0, v0.12.0, v0.13.0 are
  triaged: each is either scheduled for v0.14.0 or explicitly deferred

### Rule

No new commands are merged before CI is green and branch protection is
active on `main`.

---

## v0.14.0 — Advanced Ollama Runtime

Goal:

Turn mq-hal into a structured local reasoning layer while preserving
strict execution safety.

### Planned scope

#### Tool Registry

- [x] Add `mq_hal/tools/` directory with tool modules
- [x] Add tool metadata schema (name, description, input_schema, risk_level, requires_confirm)
- [x] Add tool capability discovery
- [x] Add tool-call validation
- [x] Add `mq-hal tools` and `mq-hal tools --json`

#### Planner

- [x] Add `mq-hal plan "<goal>"` mode
- [x] Output: Goal, Affected repos, Affected files, Risk, Steps, Validation, Rollback

#### Critic

- [x] Add `mq-hal critic plan.json` mode
- [x] Critic checks: missing tests, over-broad changes, shell execution
  risk, missing rollback, wrong repo, wrong release flow

#### Execute

- [x] Add `mq-hal execute plan.json --confirm`
- [x] Execution only after policy check and explicit confirmation

#### Model Profiles

- [x] Add `config/models.json`
- [x] Add router model profile (e.g. `qwen3:4b-instruct`, reasoning_effort: low)
- [x] Add planner model profile (e.g. `qwen3:8b`, reasoning_effort: medium)
- [x] Add critic model profile (e.g. `qwen3:8b`, reasoning_effort: high)
- [x] Add code-review model profile (e.g. `qwen2.5-coder:7b`,
  reasoning_effort: medium)
- [x] Add model selection CLI support

#### Model hardening

- [x] Add model availability check
- [x] Add model latency measurement
- [x] Add model response validation
- [x] Add better fallback to deterministic routing
- [x] Add prompt regression tests
- [x] Add invalid JSON recovery tests
- [x] Add reasoning effort profiles
- [x] Keep generation non-streaming for structured JSON enforcement
- [x] Add structured outputs enforcement

### Possible commands

```bash
mq-hal plan
mq-hal critic
mq-hal explain
mq-hal tools
mq-hal models
mq-hal model-status
mq-hal model-test
```

### Deferred carry-forward gaps

These were reviewed during v0.14.0 and intentionally kept outside the
Advanced Ollama Runtime scope:

- [x] GitHub Actions pass on `main` (from v0.11.0)
- [x] intent risk classification in intent schema (from v0.11.0)
- [x] rollback-plan field in intent schema (from v0.11.0)
- [x] requires-confirmation field in intent schema (from v0.11.0)
- [x] No new command merged without a router/smoke test (from v0.11.0)
- [x] mq-mcp runtime health in `stack-status` (Runtime observability layer)
- [x] Repo Memory: index, search, ask-repo, repo-map (from v0.12.0)
- [x] Better session summaries (from v0.13.0)

### Safety rules

- Models never execute shell directly
- Router remains authoritative
- Tool calls must be validated
- High-risk operations require confirmation
- Unsafe actions are rejected
- Model choice must not bypass router safety

---

## v0.14.5 — Visual HAL

Goal:

Connect `mq-image-analyze` vision capabilities to mq-hal for architecture
and UI reasoning.

### Planned scope

- [x] Add `mq-hal analyze-diagram <file>`
- [x] Add `mq-hal review-ui <file>`
- [x] Add `mq-hal architecture-brief <file>`
- [x] Architecture observations
- [x] Trust-boundary detection
- [x] YAML draft generation from diagrams
- [x] UI critique output

### Possible commands

```bash
mq-hal analyze-diagram architecture.png
mq-hal review-ui screenshot.png
mq-hal architecture-brief
```

### Safety requirements

- Vision input must never trigger shell execution
- Output is always read-only observation or draft YAML, never executable intent

---

## v0.15.0 — Packaged install and update flow

Goal:

Make mq-hal easier to install and maintain on a new macOS machine.

### Planned scope

- [x] Add install script
- [x] Add uninstall script
- [x] Add upgrade script
- [x] Add shell completion notes
- [x] Add PATH setup docs
- [x] Add `mq-hal doctor`
- [x] Add `mq-hal version`
- [x] Add config validation command
- [x] Add clean reinstall docs
- [x] Add optional Homebrew formula plan

### Possible commands

```bash
mq-hal version
mq-hal doctor
mq-hal config-check
mq-hal update
```

### Release gate v2

Make release a system check, not just a version bump:

- [x] `release-check.sh` blocks release if VERSION, README, CHANGELOG,
  and GitHub release tag do not all match
- [x] `release-check.sh` blocks release if any undocumented command
  exists in the registry
- [x] `release-check.sh` blocks release if any router safety test fails
- [x] `release-check.sh` supports `--dry-run`

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

- [x] Stable CLI command surface — 33 commands, enforced by release-check
- [x] Stable intent schema — `schemas/intent.schema.json` v1, validated in CI
- [x] Stable router allowlist — `ALLOWED_INTENTS` in `hal.py`, documented in
  `INTENT_CONTRACT.md`
- [x] Stable repo config format — documented in `docs/FORMATS.md`
- [x] Stable session memory format — documented in `docs/FORMATS.md`
- [x] Stable timeline output — documented in `docs/FORMATS.md`
- [x] Stable mqlaunch integration — documented in `INTEGRATION.md`
- [x] Stable mq-agent integration — documented in `INTEGRATION.md`
- [x] Stable model fallback behavior — model profiles in `config/models.json`
- [x] Complete command docs — `docs/COMMAND_SURFACE.md` + `docs/hal-command-surface.md`
- [x] Complete safety docs — `docs/INTENT_CONTRACT.md`
- [x] Complete troubleshooting docs — `docs/TROUBLESHOOTING.md`
- [x] Complete smoke tests — 29 smoke test files, all passing in CI
- [x] Complete release-check — GitHub tag gate, undocumented-command gate,
  safety gate
- [x] Green CI — GitHub Actions passing on main
- [x] Protected main branch — branch protection active on main
- [x] GitHub release — v1.0.0 released
- [x] GitHub Pages documentation — auto-deployed from main
- [x] No known critical safety gaps — audited: no shell=True, no os.system,
  intent output normalized before routing, path escape protection via
  is_within(), executor validate_command + critic gate + dry-run default.
  Critic is pattern-based (not allowlist); cat-style reads return REVIEW not
  FAIL — user sees them in dry-run and must confirm. Design decision.

---

## Future: Runtime observability layer

Goal:

Keep mq-hal focused on runtime health, diagnostics and operator summaries for
the mq ecosystem.

This layer should make the stack easier to inspect without becoming the
orchestrator.

### Planned scope

- [x] Add mq-mcp runtime health summary — `_probe_mq_mcp_http()` in
  stack-status (v1.1.0)
- [x] Add vector-store health summary — `_probe_vector_item_count()` in
  stack-status (v1.2.0)
- [x] Add model availability and latency summary — `mq-hal model-status`
- [x] Add tool availability diagnostics — `mq-hal stack-status`
- [x] Add environment-state report with secret redaction — `mq-hal env-status`
- [x] Add degraded-mode recommendations — `mq-hal env-status`

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

## Ecosystem role division

Every proposed new HAL command must answer: is this HAL's
responsibility, or does it belong in mqlaunch, repo-signal, mq-mcp,
or mq-agent?

| Repo | Role |
| --- | --- |
| `mq-hal` | interprets NL, produces status summaries and safe plans |
| `mqlaunch` | command surface, menus, terminal entrypoint |
| `repo-signal` | repo quality scoring and publish readiness |
| `mq-mcp` | MCP tool surface and local tool execution |
| `mq-agent` | orchestration and larger agent flows |

HAL summarizes and plans. It does not replace the other layers.

---

## Governance rules

These rules apply to every release, permanently:

```text
1. The allowlist is the safety boundary — never bypass it.
2. Every new command must answer: is this HAL's responsibility?
3. Intent schema is a contract — unknown intents must be rejected.
4. Command surface must be machine-readable (COMMAND_SURFACE.md).
5. Release is blocked if VERSION, README, CHANGELOG, and CI diverge.
6. Router safety tests must cover unknown intents, path escapes,
   unsafe commands, and confirm flow.
7. No new command merged without a corresponding smoke test.
```
