#!/usr/bin/env python3
"""Read-only brain control center for mq-hal."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from hal.feedback import render_feedback, surface_feedback
except ModuleNotFoundError:  # direct script execution outside the repo root
    from feedback import render_feedback, surface_feedback

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

    return surface_feedback({
        "status": status,
        "root": str(root),
        "folders": folders,
        "recent_notes": recent_notes,
        "recent_reviews": recent_reviews,
        "latest_release": rel(latest_release, root) if latest_release else None,
        "learn_lessons": learn_lessons,
        "collected_at": now_iso(),
    }, surface="Brain", command="mq-hal brain health")


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
        marker = "PASS" if meta["exists"] else "UNAVAILABLE"
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


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-._")
    return slug[:80] or "captured-page"


def defuddle_bin() -> str | None:
    env = os.environ.get("DEFUDDLE_BIN")
    if env:
        path = Path(env).expanduser()
        if path.exists():
            return str(path)
    return shutil.which("defuddle")


def url_looks_markdown(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.lower().endswith(".md")


def title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.lstrip("#").strip()
            if title:
                return title[:120]
    return fallback


def fallback_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).stem if parsed.path else ""
    return candidate.replace("-", " ").replace("_", " ").strip().title() or parsed.netloc or "Captured Page"


def unique_note_path(path: Path, overwrite: bool) -> Path:
    if overwrite or not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 1000):
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not find unique note path for {path}")


def run_defuddle(url: str, timeout: int = 60) -> dict[str, Any]:
    binary = defuddle_bin()
    command = ["defuddle", "parse", url, "--md"]
    if binary is None:
        return {
            "available": False,
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": "defuddle CLI not found",
        }

    command = [binary, "parse", url, "--md"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "command": command,
            "returncode": 124,
            "stdout": "",
            "stderr": "defuddle timed out",
        }
    except OSError as exc:
        return {
            "available": True,
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }

    return {
        "available": True,
        "command": command,
        "returncode": int(result.returncode),
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
    }


def render_capture_note(title: str, url: str, markdown: str) -> str:
    captured_at = now_iso()
    return "\n".join(
        [
            "---",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            "schema_version: web-capture.v1",
            "status: captured",
            f"source_url: {json.dumps(url, ensure_ascii=False)}",
            f"captured_at: {json.dumps(captured_at, ensure_ascii=False)}",
            "capture_tool: defuddle",
            "tags:",
            "  - web/capture",
            "  - mq/brain",
            "---",
            "",
            f"# {title}",
            "",
            f"Source: {url}",
            "",
            markdown.strip(),
            "",
        ]
    )


def brain_ingest_url(
    url: str,
    root: Path,
    folder: str,
    title: str | None,
    confirm: bool,
    overwrite: bool,
) -> dict[str, Any]:
    if url_looks_markdown(url):
        return {
            "operation": "brain_ingest_url",
            "url": url,
            "status": "rejected",
            "returncode": 2,
            "error": "URL ends in .md; defuddle skill says to use direct Markdown fetch instead.",
        }

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {
            "operation": "brain_ingest_url",
            "url": url,
            "status": "rejected",
            "returncode": 2,
            "error": "URL must be http(s).",
        }

    fallback_title = title or fallback_title_from_url(url)
    note_dir = root / folder.strip("/")
    planned_path = note_dir / f"{slugify(fallback_title)}.md"

    if not confirm:
        return {
            "operation": "brain_ingest_url",
            "url": url,
            "status": "preview",
            "requires_confirm": True,
            "root": str(root),
            "path": str(planned_path),
            "command": ["defuddle", "parse", url, "--md"],
            "returncode": 0,
        }

    result = run_defuddle(url)
    if result["returncode"] != 0:
        return {
            "operation": "brain_ingest_url",
            "url": url,
            "status": "error",
            "root": str(root),
            "path": str(planned_path),
            "defuddle": result,
            "returncode": result["returncode"],
        }

    markdown = str(result["stdout"] or "")
    final_title = title_from_markdown(markdown, fallback_title)
    note_dir = root / folder.strip("/")
    note_dir.mkdir(parents=True, exist_ok=True)
    note_path = unique_note_path(note_dir / f"{slugify(final_title)}.md", overwrite=overwrite)
    note_path.write_text(render_capture_note(final_title, url, markdown), encoding="utf-8")

    return {
        "operation": "brain_ingest_url",
        "url": url,
        "status": "captured",
        "root": str(root),
        "path": str(note_path),
        "title": final_title,
        "bytes": note_path.stat().st_size,
        "defuddle": {
            "available": result["available"],
            "command": result["command"],
            "returncode": result["returncode"],
        },
        "returncode": 0,
    }


def render_ingest_result(result: dict[str, Any]) -> None:
    print("Brain Ingest URL")
    print("================")
    print()
    print(f"url:    {result.get('url', '-')}")
    print(f"status: {result.get('status', '-')}")
    if result.get("requires_confirm"):
        print("mode:   preview; re-run with --confirm to fetch and write the note")
    if result.get("path"):
        print(f"path:   {result['path']}")
    if result.get("title"):
        print(f"title:  {result['title']}")
    if result.get("error"):
        print()
        print(result["error"])
    defuddle = result.get("defuddle")
    if isinstance(defuddle, dict) and defuddle.get("returncode") != 0:
        print()
        print(defuddle.get("stderr") or "defuddle failed")


def obsidian_bin() -> str | None:
    env = os.environ.get("OBSIDIAN_BIN")
    if env:
        path = Path(env).expanduser()
        if path.exists():
            return str(path)
    return shutil.which("obsidian")


def target_arg(note: str) -> str:
    if note.endswith((".md", ".canvas", ".base")) or "/" in note:
        return f"path={note}"
    return f"file={note}"


def run_obsidian(args: list[str], timeout: int = 20) -> dict[str, Any]:
    binary = obsidian_bin()
    command = ["obsidian", *args]
    if binary is None:
        return {
            "available": False,
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": "obsidian CLI not found",
        }

    command = [binary, *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "command": command,
            "returncode": 124,
            "stdout": "",
            "stderr": "obsidian CLI timed out",
        }
    except OSError as exc:
        return {
            "available": True,
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }

    return {
        "available": True,
        "command": command,
        "returncode": int(result.returncode),
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
    }


def brain_open(note: str, vault: str | None = None) -> dict[str, Any]:
    args = []
    if vault:
        args.append(f"vault={vault}")
    args.extend(["read", target_arg(note)])
    result = run_obsidian(args)
    result["note"] = note
    result["operation"] = "brain_open"
    return result


def brain_sync_status(note: str, status: str, vault: str | None = None, confirm: bool = False) -> dict[str, Any]:
    args = []
    if vault:
        args.append(f"vault={vault}")
    args.extend(["property:set", "name=status", f"value={status}", target_arg(note)])

    if not confirm:
        return {
            "available": obsidian_bin() is not None,
            "operation": "brain_sync_status",
            "note": note,
            "status": status,
            "requires_confirm": True,
            "command": ["obsidian", *args],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        }

    result = run_obsidian(args)
    result["note"] = note
    result["status"] = status
    result["operation"] = "brain_sync_status"
    return result


def render_obsidian_result(result: dict[str, Any]) -> None:
    operation = str(result.get("operation") or "obsidian")
    title = "Brain Open" if operation == "brain_open" else "Brain Sync Status"
    print(title)
    print("=" * len(title))
    print()
    if not result.get("available"):
        print("obsidian: unavailable")
        print("Install or expose the Obsidian CLI, then retry with Obsidian open.")
        return
    if result.get("requires_confirm"):
        print("Preview only. Re-run with --confirm to update Obsidian.")
        print()
    print(f"note:       {result.get('note', '-')}")
    if operation == "brain_sync_status":
        print(f"status:     {result.get('status', '-')}")
    print(f"returncode: {result.get('returncode', '-')}")
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    if stdout:
        print()
        print(stdout)
    if stderr:
        print()
        print(stderr)


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

    p_ingest = sub.add_parser("ingest-url", help="Capture a web page into Obsidian via Defuddle")
    p_ingest.add_argument("url")
    p_ingest.add_argument("--folder", default="inbox")
    p_ingest.add_argument("--title")
    p_ingest.add_argument("--root", help="Override mqobsidian root")
    p_ingest.add_argument("--overwrite", action="store_true")
    p_ingest.add_argument("--confirm", action="store_true")
    p_ingest.add_argument("--json", action="store_true")

    p_open = sub.add_parser("open", help="Read/open a brain note through obsidian CLI")
    p_open.add_argument("note")
    p_open.add_argument("--vault")
    p_open.add_argument("--json", action="store_true")

    p_sync = sub.add_parser("sync-status", help="Set a note status property through obsidian CLI")
    p_sync.add_argument("note")
    p_sync.add_argument("--status", required=True)
    p_sync.add_argument("--vault")
    p_sync.add_argument("--confirm", action="store_true")
    p_sync.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).expanduser() if args.root else None

    if args.sample:
        data = surface_feedback(SAMPLE, surface="Brain", command="mq-hal brain health")
    elif args.command == "search":
        root_path = root or resolve_root()
        payload = search(root_path, " ".join(args.query), args.limit)
        if args.json:
            print_json(payload)
        else:
            render_search(payload)
        return 0
    elif args.command == "ingest-url":
        payload = brain_ingest_url(
            args.url,
            root=root or resolve_root(),
            folder=args.folder,
            title=args.title,
            confirm=args.confirm,
            overwrite=args.overwrite,
        )
        if args.json:
            print_json(payload)
        else:
            render_ingest_result(payload)
        return 0 if payload["returncode"] == 0 else int(payload["returncode"])
    elif args.command == "open":
        payload = brain_open(args.note, vault=args.vault)
        if args.json:
            print_json(payload)
        else:
            render_obsidian_result(payload)
        return 0 if payload["returncode"] == 0 else 1
    elif args.command == "sync-status":
        payload = brain_sync_status(
            args.note,
            status=args.status,
            vault=args.vault,
            confirm=args.confirm,
        )
        if args.json:
            print_json(payload)
        else:
            render_obsidian_result(payload)
        return 0 if payload["returncode"] == 0 else 1
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
    print()
    render_feedback(data["feedback"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
