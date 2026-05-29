---
name: repo-aware
description: Use when inspecting, explaining, planning, reviewing, or changing mq-hal with repository-specific context.
---

# Repo Aware

Use this skill to keep work grounded in mq-hal's actual local HAL router architecture.

## What This Repo Is

`mq-hal` is a local macOS HAL-style command router. It takes natural language, asks Ollama for a strict JSON intent, then routes that intent through safe Python code and whitelisted local actions. The model never runs shell directly.

Primary surfaces:

- `bin/mq-hal` for the public command wrapper and subcommand dispatch
- `scripts/hal.py` for intent schema, deterministic fallback, repo selection, and routing
- `scripts/*.py` for read-only reports, doctor summary, fix planning, timeline, and memory
- `prompts/system.txt`, `prompts/doctor-summary.txt`, and `prompts/fix-planner.txt` for model behavior
- `config/repos.json` for known local repos
- `tests/*-smoke.sh` for command contract checks
- `docs/hal-command-surface.md`, `docs/INTEGRATION.md`, and `docs/index.html` for public docs

## First Inspection

Start with:

```bash
git status --short
rg --files
sed -n '1,240p' README.md
sed -n '1,220p' bin/mq-hal
sed -n '1,260p' scripts/hal.py
```

If changing routing or safety, inspect:

```bash
rg "ALLOWED_INTENTS|ALLOWED_MQLAUNCH|subprocess|shell|confirm|repo" scripts/hal.py scripts/*.py
sed -n '1,220p' prompts/system.txt
sed -n '1,220p' tests/hal-router-smoke.sh
```

## Verification

Use focused checks:

```bash
python3 -m py_compile scripts/hal.py
./tests/hal-router-smoke.sh
./tests/smoke.sh
```

For broader changes:

```bash
./release-check.sh
```

## Guardrails

- Preserve the rule that Ollama returns intent JSON and Python decides what is allowed.
- Do not add direct shell execution from model output.
- Keep repo actions scoped to configured repos in `config/repos.json`.
- Keep write or risky actions behind explicit confirmation.
- Prefer deterministic fallback behavior when Ollama is unavailable.
- Update docs and smoke tests when command behavior changes.
