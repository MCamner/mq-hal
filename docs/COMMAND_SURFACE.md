# Command Surface

Canonical registry of all named `mq-hal` commands.

Every command listed here must have:

- a case entry in `bin/mq-hal`
- a smoke test
- documentation in `docs/hal-command-surface.md`

The detailed reference with flags, examples, and backend notes is in
`docs/hal-command-surface.md`.

---

## Named commands

| Command | Aliases | AI | Memory | Confirm | mqlaunch |
| --------------- | --------------------------------- | --- | ------ | ------- | -------------------- |
| `brief` | — | Yes | Yes | No | `hal brief` |
| `audit` | — | Yes | Yes | No | `hal audit` |
| `stack-status` | `stack`, `status-stack`, `status` | No | No | No | — |
| `release-brief` | — | Yes | Yes | No | `hal release-brief` |
| `release` | — | No | No | No | — |
| `runtime` | — | No | No | No | — |
| `provenance` | — | No | No | No | — |
| `compatibility` | — | No | No | No | — |
| `route` | — | No | No | No | — |
| `feedback` | — | No | No | No | `feedback` |
| `dashboard` | no-argument `mq-hal` | No | No | No | — |
| `repo-status` | `repo` | No | No | No | `hal repo-status` |
| `ci` | `ci-status` | No | No | No | `hal ci` |
| `doctor-summary` | `doctor` | Yes | Yes | No | `hal doctor` |
| `fix-doctor` | `doctor-fix`, `fix-planner`, `plan-fix` | Yes | Yes | No | `hal fix-doctor` |
| `session` | `memory` | No | No | No | `hal session` |
| `last` | — | No | No | No | `hal last` |
| `remember` | — | No | Yes | No | `hal remember` |
| `timeline` | — | No | No | No | `hal timeline` |
| `history` | — | No | No | No | — |
| `alerts` | — | No | No | No | — |
| `changes` | — | No | No | No | — |
| `next` | — | No | No | No | — |
| `fix` | — | No | No | Yes | — |
| `open` | — | No | No | Yes | — |
| `memory-path` | `session-path` | No | No | No | `hal memory-path` |
| `memory-status` | `memory-brief` | No | No | No | — |
| `brain` | — | No | No | No | — |
| `context` | — | No | No | No | — |
| `index` | — | No | Yes | No | — |
| `search` | — | No | No | No | — |
| `ask-repo` | — | No | No | No | — |
| `repo-map` | — | No | No | No | — |
| `agent-brief` | `agent` | No | No | No | — |
| `hello` | `status-screen` | No | No | No | — |
| `tools` | — | No | No | No | — |
| `models` | `model-profiles` | No | No | No | — |
| `model-status` | — | No | No | No | — |
| `model-test` | — | Yes | No | No | — |
| `version` | `--version` | No | No | No | — |
| `config-check` | `config` | No | No | No | — |
| `update` | `upgrade` | No | No | Yes | — |
| `analyze-diagram` | — | No | No | No | — |
| `review-ui` | — | No | No | No | — |
| `architecture-brief` | — | No | No | No | — |
| `plan` | — | Yes | No | No | — |
| `code-plan` | — | Cloud | No | No | — |
| `critic` | — | No | No | No | — |
| `execute` | — | No | No | Yes | — |
| `learn` | — | No | Yes | No | — |
| `env-status` | `env` | No | No | No | — |

**AI** — calls Ollama when available; falls back to deterministic output.
Visual commands can include local `mq-image-analyze` output when that tool is
installed, but remain read-only and deterministic without it.
**AI: Cloud** — sends data to an external provider named on the command line.
`code-plan` is the only command in this table that does, it never runs without
`--provider`, and no other command can be made to by configuration. The terms
are `docs/CLOUD_PROVIDER_BOUNDARY.md`.
**Memory** — writes to `~/.mq-hal/session.jsonl` (session events) or
`~/.mq-hal/learn/lessons.jsonl` (`learn add`) unless `--no-memory` is
passed.
**Confirm** — prompts before executing. `execute` requires `--confirm`, and
plan steps marked `requires_confirm` ask again before running. `create_branch`
in the router always confirms regardless. `update` previews by default and
requires `--confirm` before running `git pull --ff-only`.

## Operator feedback contract

The main operator controls (`stack`, `release`, `runtime`, `route`, `brain`, `context`,
`dashboard`, `next`, `open`, and `fix`) expose `mq.feedback.v1`. Its status is
one of `PASS`, `WARN`, `FAIL`, `SKIPPED`, or `UNAVAILABLE`. Actionable results
include `next_action.text`, `command`, `safety`, and `requires_confirmation`.
Feedback is advisory and never executes the suggested command.

---

## Router commands (free prompt)

These are handled by the intent router in `scripts/hal.py`. All require
Ollama unless `--no-ai` is passed.

| Flag / form | Description |
| ------------------------------ | ----------------------------------------- |
| `mq-hal "prompt"` | Natural-language intent routing |
| `mq-hal --raw-intent "prompt"` | Print parsed JSON intent, no execution |
| `mq-hal --explain-intent "p"` | Print intent and resolved repo |
| `mq-hal --confirm "prompt"` | Preview command and ask before running |
| `mq-hal --no-ai "prompt"` | Deterministic routing without Ollama |
| `mq-hal --model <profile> "prompt"` | Use a profile from `config/models.json` |
| `mq-hal --list-repos` | List configured repos |
| `mq-hal --cd <repo>` | Print repo path for shell `cd` |

---

## Router intent allowlist

See `schemas/intent.schema.json` for the formal schema and
`docs/INTENT_CONTRACT.md` for the full safety contract.

| Intent | Safety class | Always confirms |
| --------------- | ------------ | --------------- |
| `help` | read-only | No |
| `list_repos` | read-only | No |
| `print_cd` | read-only | No |
| `pwd` | read-only | No |
| `repo_tree` | read-only | No |
| `git_status` | read-only | No |
| `git_log` | read-only | No |
| `grep_repo` | read-only | No |
| `repo_status_json` | read-only | No |
| `switch_repo` | state-write | No |
| `run_test` | exec | No |
| `open_editor` | exec | No |
| `run_mqlaunch` | mqlaunch-allowlisted | No |
| `create_branch` | repo-write | Yes |
| `refuse` | no-op | — |

## Changed-file verification

```bash
mq-hal audit --repo mq-agent --verification --json
mq-hal stack-status --verification --json
mq-hal stack-status --legacy --verification
```

Both views separate structural/runtime status from changed-file evidence. With
`--verification`, HAL reads `repo-signal doctor <configured-path> --verification
--json`; repo-signal delegates existing-receipt validation to mq-agent. HAL runs
no test, writes no receipt and calls no cloud provider. Use trusted installed
repo-signal and mq-agent executables.

Without the flag, verification is `NOT_VERIFIED` and no doctor process starts.
Samples stay offline even with the flag. Missing/older providers, invalid JSON,
timeouts and invalid verification fields remain `NOT_VERIFIED`. Repo-signal with
its doctor verification extension and mq-agent with verify-changes are required.

Audit adds `verification`. Stack adds a HAL presentation map `verification`
keyed by repository name and `verification_summary`. Existing cockpit fields
and HAL feedback are preserved; verification_summary is a separate verdict:
FAIL precedes STALE, which precedes NOT_VERIFIED, and only a nonempty set of PASS
results gives PASS. Unconfigured cockpit items remain NOT_VERIFIED; producer
paths are never used to launch doctor. The cockpit label `mqlaunch` resolves to
`macos-scripts` unless explicitly configured; `mqobsidian` is registered by default. Each local read has a 35-second timeout,
so an explicitly requested multi-repo check can take longer than ordinary stack.

Status is PASS, FAIL, STALE or NOT_VERIFIED, with fixed advisory `next_action`
text. Actions are never executed. A PASS covers changed files against HEAD,
not the full test suite, GitHub CI or release approval. A passing structural
`overall` or runtime feedback does not override verification status. Raw doctor
reports, paths, stderr and receipt bodies are not copied into verification.
