#!/usr/bin/env python3
"""Read-only brain control center for mq-hal."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(
    os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))
).expanduser()

BRAIN_FOLDERS = ("memory", "learn", "truth", "reviews")
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}

SAMPLE: dict[str, Any] = {
    "status": "ok",
    "root": "~/mqobsidian",
    "folders": {
        "memory": {"exists": True, "count": 12, "latest": "memory/2026-06-12-note.md"},
        "learn": {"exists": True, "count": 4, "latest": "learn/export.jsonl"},
        "truth": {"exists": True, "count": 3, "latest": "truth/latest-release.md"},
        "reviews": {"exists": True, "count": 7, "latest": "reviews/review-2026-06-12.md"},
    },
    "recent_notes": ["memory/2026-06-12-note.md"],
    "recent_reviews": ["reviews/review-2026-06-12.md"],
    "latest_release": "truth/latest-release.md",
    "learn_lessons": 2,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def brain_candidates() -> list[Path]:
    candidates: list[Path] = []
    for key in ("MQ_HAL_BRAIN_DIR", "MQOBSIDIAN_PATH", "MQ_OBSIDIAN_PATH"):
        value = os.environ.get(key)
        if value:
            candidates.append(Path(value).expanduser())

    candidates.extend(
        [
            Path.home() / "mqobsidian",
            Path.home() / "mq-obsidian",
            Path.home() / "Obsidian" / "MQ",
            STATE_DIR,
        ]
    )
    return candidates


def resolve_root() -> Path:
    for candidate in brain_candidates():
        if candidate.exists() and candidate.is_dir():
            return candidate
    return brain_candidates()[0]


def is_text(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def iter_text_files(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if any(part.startswith(".") for part in path.parts):
            continue
        if is_text(path):
            files.append(path)
    return files


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def latest(files: list[Path]) -> Path | None:
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                count += 1
    except OSError:
        return 0
    return count


def collect(root: Path | None = None) -> dict[str, Any]:
    root = root or resolve_root()
    folders: dict[str, Any] = {}
    all_files: dict[str, list[Path]] = {}

    for name in BRAIN_FOLDERS:
        folder = root / name
        files = iter_text_files(folder)
        all_files[name] = files
        newest = latest(files)
        folders[name] = {
            "exists": folder.exists() and folder.is_dir(),
            "count": len(files),
            "latest": rel(newest, root) if newest else None,
        }

    learn_lessons = read_jsonl_count(STATE_DIR / "learn" / "lessons.jsonl")
    if learn_lessons and folders["learn"]["count"] == 0:
        folders["learn"]["count"] = learn_lessons
        folders["learn"]["latest"] = str(STATE_DIR / "learn" / "lessons.jsonl")

    recent_notes = [
        rel(path, root)
        for path in sorted(
            all_files["memory"],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:5]
    ]
    recent_reviews = [
        rel(path, root)
        for path in sorted(
            all_files["reviews"],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:5]
    ]
    release_files = [
        path for path in all_files["truth"] + all_files["reviews"]
        if "release" in path.name.lower()
    ]
    latest_release = latest(release_files)

    missing = [
        name for name, meta in folders.items()
        if not meta["exists"]
    ]
    status = "ok" if not missing else ("warn" if root.exists() else "missing")

    return {
        "status": status,
        "root": str(root),
        "folders": folders,
        "recent_notes": recent_notes,
        "recent_reviews": recent_reviews,
        "latest_release": rel(latest_release, root) if latest_release else None,
        "learn_lessons": learn_lessons,
        "collected_at": now_iso(),
    }


def search(root: Path, query: str, limit: int) -> dict[str, Any]:
    terms = [term.lower() for term in query.split() if term.strip()]
    results: list[dict[str, Any]] = []
    for folder_name in BRAIN_FOLDERS:
        for path in iter_text_files(root / folder_name):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            haystack = f"{path.name}\n{text}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score <= 0:
                continue
            preview = " ".join(text.strip().split())[:180]
            results.append(
                {
                    "path": rel(path, root),
                    "folder": folder_name,
                    "score": score,
                    "preview": preview,
                }
            )

    results.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return {"query": query, "root": str(root), "results": results[:limit]}


def render_health(data: dict[str, Any]) -> None:
    print("Brain Health")
    print("============")
    print()
    print(f"Status: {data['status']}")
    print(f"Root:   {data['root']}")
    print()
    for name, meta in data["folders"].items():
        marker = "OK" if meta["exists"] else "MISS"
        latest_item = meta["latest"] or "-"
        print(f"{marker:<5} {name:<8} count={meta['count']:<4} latest={latest_item}")


def render_recent(data: dict[str, Any]) -> None:
    print("Brain Recent")
    print("============")
    print()
    print("Recent notes")
    print("------------")
    for item in data["recent_notes"] or ["-"]:
        print(item)
    print()
    print("Recent reviews")
    print("--------------")
    for item in data["recent_reviews"] or ["-"]:
        print(item)
    print()
    print("Latest release")
    print("--------------")
    print(data["latest_release"] or "-")


def render_summary(data: dict[str, Any]) -> None:
    print("Brain Control Center")
    print("====================")
    print()
    print(f"Status: {data['status']}")
    print(f"Root:   {data['root']}")
    print()
    print("Exports")
    print("-------")
    labels = {
        "memory": "brain notes",
        "learn": "learn exports",
        "truth": "truth exports",
        "reviews": "review exports",
    }
    for name in BRAIN_FOLDERS:
        meta = data["folders"][name]
        print(f"{labels[name]:<16} {meta['count']}")
    print()
    render_recent(data)


def render_search(payload: dict[str, Any]) -> None:
    print("Brain Search")
    print("============")
    print()
    print(f"Query: {payload['query']}")
    print()
    if not payload["results"]:
        print("No matches.")
        return
    for item in payload["results"]:
        print(f"[{item['score']}] {item['path']}  folder={item['folder']}")
        if item["preview"]:
            print(f"    {item['preview']}")


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal brain",
        description="Read-only control center for mqobsidian and local HAL memory.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--root", help="Override mqobsidian root")

    sub = parser.add_subparsers(dest="command")
    p_health = sub.add_parser("health", help="Show folder health")
    p_health.add_argument("--json", action="store_true")

    p_recent = sub.add_parser("recent", help="Show recent notes, reviews and release export")
    p_recent.add_argument("--json", action="store_true")

    p_search = sub.add_parser("search", help="Search brain notes and exports")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("--limit", type=int, default=8)
    p_search.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).expanduser() if args.root else None

    if args.sample:
        data = SAMPLE
    elif args.command == "search":
        root_path = root or resolve_root()
        payload = search(root_path, " ".join(args.query), args.limit)
        if args.json:
            print_json(payload)
        else:
            render_search(payload)
        return 0
    else:
        data = collect(root)

    if args.json:
        print_json(data)
        return 0

    if args.command == "health":
        render_health(data)
    elif args.command == "recent":
        render_recent(data)
    else:
        render_summary(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
