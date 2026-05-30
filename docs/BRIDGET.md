# Bridget and HAL

## Roles

**HAL** (`mq-hal`) is the local command router. It:

- Interprets natural-language prompts via Ollama
- Produces structured JSON intents
- Routes commands through a safe allowlist
- Summarizes repo and stack state
- Plans, diagnoses, and reports — never acts on its own authority

**Bridget** is the optional terminal persona layer. It:

- Names the HAL experience in mqlaunch menus
- Can provide voice output in the future (see `docs/VOICE_MODE.md`)
- Lives in `macos-scripts` as a thin bridge — not in mq-hal

## Architecture

```text
User
  ↓
mqlaunch (Bridget — terminal UX, menus, entrypoint)
  ↓
mq-hal (router — intent, safety, summaries)
  ↓
git / mqlaunch / repo-signal / mq-agent / mq-mcp
```

Bridget is UX. HAL is engine.

## Design rules

- Bridget provides personality, not safety logic
- The HAL allowlist governs execution, not Bridget
- Voice toggles are UI only — the safety model is unchanged
- Bridget delegates to mq-hal; it never duplicates HAL logic
- New features belong in mq-hal first, then exposed via Bridget

## Identity

HAL is a deliberate reference to HAL 9000 — but one that knows its
limits and refuses unsafe commands by design.

mq-hal summarizes, plans, and suggests.
It asks before acting on anything write-capable.
It refuses what it does not recognize.
