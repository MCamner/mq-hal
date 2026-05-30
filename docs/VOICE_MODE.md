# Voice Mode Design

Optional voice interface for HAL. Off by default. Local-only by design.

---

## Principles

- **Local-only**: no cloud TTS or STT dependency by default
- **Explicit**: voice input triggers the same router and confirm flow
  as text — no automatic execution
- **Off by default**: requires an explicit toggle to activate
- **Thin layer**: voice is input/output only — the safety model,
  allowlist, and intent contract are unchanged

---

## Non-goals

- No always-on microphone
- No hidden recording or logging of audio
- No cloud voice API calls by default
- No command execution from voice without passing through the router
- No special permissions for voice that text does not have

---

## Proposed design (future)

### Toggle

```bash
mqlaunch hal bridget-on    # enable voice output for HAL responses
mqlaunch hal bridget-off   # disable voice output
mq-hal --voice "kör doctor"  # one-off voice input
```

### Input pipeline

```text
microphone
  ↓
local STT (e.g. whisper.cpp or macOS Speech framework)
  ↓
text prompt
  ↓
mq-hal router (same intent contract as text)
  ↓
confirm step (same as --confirm)
  ↓
execute allowlisted command
```

### Output pipeline

```text
HAL text response
  ↓
local TTS (e.g. macOS say, piper, or coqui-tts)
  ↓
audio output
```

---

## Bridget voice toggle

Bridget is the HAL persona that can respond via voice. The toggle
controls whether HAL speaks its responses — it does not change what
HAL is allowed to do.

```bash
# future mqlaunch menu options
mqlaunch hal bridget-on    # HAL responses are spoken via local TTS
mqlaunch hal bridget-off   # HAL responses are text-only (default)
```

The Bridget voice toggle is a presentation preference stored in
`~/.mq-hal/state.json`. It has no effect on routing, allowlists,
confirmation requirements, or session memory.

---

## Safety constraints

Any voice implementation must satisfy:

- Voice input is processed as text before routing
- The intent contract and allowlist apply identically to voice input
- High-risk intents still require explicit confirmation
- The `refuse` intent applies to voice the same way as text
- Audio is never stored without explicit user opt-in

---

## Implementation status

Not yet implemented. This document records the design intent so future
work starts from the right constraints.
