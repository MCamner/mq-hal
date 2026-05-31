# mq-hal Terminal Demo

An ASCII-only walkthrough of the local HAL flow.

```text
$ mq-hal hello

HAL
===

Active repo:  mq-hal
Version:      0.14.2

Memory:       memory: missing-vector-store  mq-agent=ok  repo-signal=ok

Recent session
--------------
  2026-05-31 01:20  brief           mq-hal          healthy
  2026-05-31 01:18  note            mq-hal          release looked good

Session summary
---------------
  brief                1
  note                 1

Commands
--------
  brief                 repo status snapshot
  doctor-summary        local health summary
  release-brief         release readiness check
  timeline              full session history
  memory-status         semantic memory state
  agent-brief           mq-agent summary
  stack-status          full stack overview
```

```text
$ mq-hal timeline --compact

TIME              TYPE             REPO
2026-05-31 01:20  brief            mq-hal
2026-05-31 01:18  note             mq-hal
```

```text
$ mq-hal plan "prepare release notes" --out plan.json
$ mq-hal critic plan.json
$ mq-hal execute plan.json

HAL Execute
===========

Steps (dry run - add --confirm to execute)
------------------------------------------
  1. Review current release notes
     $ cat CHANGELOG.md

Run:  mq-hal execute plan.json --confirm
```

The demo is static documentation. It does not execute commands and is safe to
show in README, GitHub Pages, or release notes.
