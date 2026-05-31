#!/usr/bin/env python3
"""mq-hal learn: local lesson storage for verified learnings."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(
    os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
).expanduser()
LEARN_DIR = STATE_DIR / "learn"
LESSONS_PATH = LEARN_DIR / "lessons.jsonl"

VALID_SOURCES = {"codex", "claude", "manual"}

# Patterns for secret-like values that should be redacted before write.
_SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(bearer\s+)\S+", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{36,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{32,}", re.IGNORECASE),
]


def _redact_simple(text: str) -> str:
    """Apply all secret patterns, replacing the secret value with [REDACTED]."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_replace_secret, text)
    return text


def _replace_secret(m: re.Match) -> str:
    full = m.group(0)
    # Find the last "word" (the secret value) and redact it.
    return re.sub(r"(\S+)$", "[REDACTED]", full)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_learn_dir() -> None:
    LEARN_DIR.mkdir(parents=True, exist_ok=True)


def load_lessons() -> list[dict[str, Any]]:
    if not LESSONS_PATH.exists():
        return []
    lessons: list[dict[str, Any]] = []
    for line in LESSONS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            lessons.append(obj)
    return lessons


def save_lesson(lesson: dict[str, Any]) -> None:
    ensure_learn_dir()
    with LESSONS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(lesson, ensure_ascii=False) + "\n")


def cmd_add(args: argparse.Namespace) -> int:
    source = args.source.strip().lower()
    if source not in VALID_SOURCES:
        print(
            f"ERROR: --source must be one of: {', '.join(sorted(VALID_SOURCES))}",
            file=sys.stderr,
        )
        return 2

    task = _redact_simple(args.task.strip())
    lesson_text = _redact_simple(args.lesson.strip())
    validation = _redact_simple(args.validation.strip()) if args.validation else ""

    if not task or not lesson_text:
        print("ERROR: --task and --lesson must not be empty", file=sys.stderr)
        return 2

    lesson: dict[str, Any] = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": now_iso(),
        "repo": args.repo or None,
        "source": source,
        "task": task,
        "lesson": lesson_text,
        "validation": validation,
    }

    save_lesson(lesson)

    if args.json:
        print(json.dumps(lesson, indent=2, ensure_ascii=False))
    else:
        print(f"Saved lesson {lesson['id']}.")
        print(f"  repo:   {lesson['repo'] or '(none)'}")
        print(f"  source: {lesson['source']}")
        print(f"  task:   {lesson['task'][:72]}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    lessons = load_lessons()

    if args.repo:
        lessons = [l for l in lessons if l.get("repo") == args.repo]
    if args.source:
        lessons = [l for l in lessons if l.get("source") == args.source.lower()]

    if not lessons:
        print("No lessons found.")
        return 0

    if args.json:
        print(json.dumps(lessons, indent=2, ensure_ascii=False))
        return 0

    for l in lessons:
        ts = str(l.get("timestamp", ""))[:16]
        lid = l.get("id", "?")
        repo = (l.get("repo") or "-")[:14]
        src = (l.get("source") or "-")[:8]
        task = str(l.get("task", ""))[:48]
        print(f"{ts}  [{lid}]  {src:8}  repo={repo:14}  {task}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    lessons = load_lessons()
    matches = [l for l in lessons if l.get("id", "").startswith(args.id)]

    if not matches:
        print(f"ERROR: no lesson found with id starting with {args.id!r}", file=sys.stderr)
        return 2

    if len(matches) > 1:
        print(f"ERROR: ambiguous id prefix {args.id!r} — {len(matches)} matches", file=sys.stderr)
        return 2

    lesson = matches[0]

    if args.json:
        print(json.dumps(lesson, indent=2, ensure_ascii=False))
        return 0

    print(f"Lesson {lesson.get('id')}")
    print("=" * 40)
    print(f"Timestamp:  {lesson.get('timestamp', '-')}")
    print(f"Repo:       {lesson.get('repo') or '(none)'}")
    print(f"Source:     {lesson.get('source', '-')}")
    print()
    print(f"Task")
    print(f"----")
    print(lesson.get("task", ""))
    print()
    print(f"Lesson")
    print(f"------")
    print(lesson.get("lesson", ""))
    if lesson.get("validation"):
        print()
        print(f"Validation")
        print(f"----------")
        print(lesson["validation"])
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    lessons = load_lessons()
    query = args.query.lower()

    results = [
        l for l in lessons
        if query in str(l.get("task", "")).lower()
        or query in str(l.get("lesson", "")).lower()
        or query in str(l.get("validation", "")).lower()
        or query in str(l.get("repo", "")).lower()
    ]

    if not results:
        print(f"No lessons matched {args.query!r}.")
        return 0

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    for l in results:
        ts = str(l.get("timestamp", ""))[:16]
        lid = l.get("id", "?")
        repo = (l.get("repo") or "-")[:14]
        src = (l.get("source") or "-")[:8]
        task = str(l.get("task", ""))[:48]
        print(f"{ts}  [{lid}]  {src:8}  repo={repo:14}  {task}")

    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    lessons = load_lessons()

    if args.repo:
        lessons = [l for l in lessons if l.get("repo") == args.repo]

    if not lessons:
        print("No lessons to summarize.")
        return 0

    by_source: dict[str, int] = {}
    by_repo: dict[str, int] = {}
    for l in lessons:
        src = l.get("source") or "unknown"
        repo = l.get("repo") or "(none)"
        by_source[src] = by_source.get(src, 0) + 1
        by_repo[repo] = by_repo.get(repo, 0) + 1

    if args.json:
        print(json.dumps({
            "total": len(lessons),
            "by_source": by_source,
            "by_repo": by_repo,
            "latest": lessons[-1] if lessons else None,
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"HAL Learn Summary")
    print(f"=================")
    print(f"Total lessons: {len(lessons)}")
    print()
    print("By source:")
    for src, count in sorted(by_source.items()):
        print(f"  {src:12} {count}")
    print()
    print("By repo:")
    for repo, count in sorted(by_repo.items()):
        print(f"  {repo:18} {count}")
    print()
    latest = lessons[-1]
    print(f"Latest: [{latest.get('id')}] {str(latest.get('task', ''))[:60]}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal learn",
        description="Store and retrieve verified local learnings.",
    )
    sub = parser.add_subparsers(dest="subcommand")

    p_add = sub.add_parser("add", help="Add a new lesson")
    p_add.add_argument("--repo", help="Repo this lesson applies to")
    p_add.add_argument(
        "--source", required=True,
        choices=sorted(VALID_SOURCES),
        help="Origin of the lesson",
    )
    p_add.add_argument("--task", required=True, help="What was being done")
    p_add.add_argument("--lesson", required=True, help="What was learned")
    p_add.add_argument("--validation", default="", help="How it was verified")
    p_add.add_argument("--json", action="store_true", help="JSON output")

    p_list = sub.add_parser("list", help="List lessons")
    p_list.add_argument("--repo", help="Filter by repo")
    p_list.add_argument("--source", help="Filter by source")
    p_list.add_argument("--json", action="store_true", help="JSON output")

    p_show = sub.add_parser("show", help="Show a lesson by id")
    p_show.add_argument("id", help="Lesson id (prefix match)")
    p_show.add_argument("--json", action="store_true", help="JSON output")

    p_search = sub.add_parser("search", help="Search lessons")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--json", action="store_true", help="JSON output")

    p_sum = sub.add_parser("summarize", help="Summarize all lessons")
    p_sum.add_argument("--repo", help="Limit to repo")
    p_sum.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args(argv)

    if args.subcommand == "add":
        return cmd_add(args)
    if args.subcommand == "list":
        return cmd_list(args)
    if args.subcommand == "show":
        return cmd_show(args)
    if args.subcommand == "search":
        return cmd_search(args)
    if args.subcommand == "summarize":
        return cmd_summarize(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
