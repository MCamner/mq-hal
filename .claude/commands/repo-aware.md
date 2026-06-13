# Repo Aware

Use the Codex `repo-aware` skill before answering or changing this repository.

Skill file:

```text
/Users/mansys/.codex/skills/repo-aware/SKILL.md
```

First read that file completely and follow its workflow. If the file is not
available, fall back to:

```text
skills/repo-aware/SKILL.md
```

Default inspection pass:

```bash
git status --short
rg --files
sed -n '1,220p' README.md
```

If `repo-signal` is available and relevant, use it as context:

```bash
repo-signal doctor
repo-signal analyze
```

User request:

```text
$ARGUMENTS
```

After inspecting, do the smallest grounded action that helps the request.
Preserve user changes, update docs or smoke tests when command behavior changes,
and report what was changed and verified.
