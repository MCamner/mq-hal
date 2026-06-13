#!/usr/bin/env python3
"""Timeline and history views for mq-hal operator state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from hal import dashboard as dashboard_control  # noqa: E402


MQ_AGENT_STATE_DIR = Path(
    os.environ.get("MQ_AGENT_STATE_DIR", str(Path.home() / ".mq-agent"))
).expanduser()
BRAIN_ROOT = Path(
    os.environ.get("MQ_HAL_BRAIN_ROOT")
    or os.environ.get("MQOBSIDIAN_PATH")
    or str(Path.home() / "mqobsidian")
).expanduser()
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}


SAMPLE: dict[str, Any] = {
    "title": "HAL History",
    "sources": {
        "mq_agent": "~/.mq-agent",
        "brain": "~/mqobsidian",
    },
    "stack_score": [
        {"date": "2026-06-11", "score": 88, "source": "stack-history.jsonl"},
        {"date": "2026-06-12", "score": 92, "source": "stack-history.jsonl"},
    ],
    "brain_growth": [
        {"date": "2026-06-11", "files": 3},
        {"date": "2026-06-12", "files": 5},
    ],
    "release_history": [
        {"date": "2026-06-12", "path": "truth/latest-release.md"},
    ],
}


def _date_from_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def _iter_files(root: Path, suffixes: set[str] | None = None) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if not path.is_file():
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        files.append(path)
    return files


def _load_json_objects(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return []
    if not text:
        return []

    objects: list[dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        for line in text.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                objects.append(item)
        return objects

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        objects.append(parsed)
    elif isinstance(parsed, list):
        objects.extend(item for item in parsed if isinstance(item, dict))
    return objects


def _extract_score(item: dict[str, Any]) -> int | None:
    for key in ("score", "stack_score", "overall_score"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    overall = item.get("overall")
    if isinstance(overall, dict):
        value = overall.get("score")
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _extract_date(item: dict[str, Any], fallback: Path) -> str:
    for key in ("date", "timestamp", "created_at", "updated_at"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value[:10]
    return _date_from_mtime(fallback)


def stack_score_history(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _iter_files(root, {".json", ".jsonl"}):
        if "stack" not in path.name.lower() and "cockpit" not in path.name.lower():
            continue
        for item in _load_json_objects(path):
            score = _extract_score(item)
            if score is None:
                continue
            rows.append({
                "date": _extract_date(item, path),
                "score": score,
                "source": str(path.relative_to(root)),
            })
    rows.sort(key=lambda item: (str(item["date"]), str(item["source"])))
    return rows[-20:]


def brain_growth(root: Path) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for path in _iter_files(root, TEXT_SUFFIXES):
        counts[_date_from_mtime(path)] += 1
    return [
        {"date": date, "files": count}
        for date, count in sorted(counts.items())[-20:]
    ]


def release_history(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _iter_files(root, TEXT_SUFFIXES):
        rel = str(path.relative_to(root))
        haystack = rel.lower()
        if "release" not in haystack and "version" not in haystack:
            continue
        rows.append({"date": _date_from_mtime(path), "path": rel})
    rows.sort(key=lambda item: (str(item["date"]), str(item["path"])))
    return rows[-20:]


def collect_history(
    mq_agent_root: Path | None = None,
    brain_root: Path | None = None,
) -> dict[str, Any]:
    mq_agent_root = mq_agent_root or MQ_AGENT_STATE_DIR
    brain_root = brain_root or BRAIN_ROOT
    return {
        "title": "HAL History",
        "sources": {
            "mq_agent": str(mq_agent_root),
            "brain": str(brain_root),
        },
        "stack_score": stack_score_history(mq_agent_root),
        "brain_growth": brain_growth(brain_root),
        "release_history": release_history(brain_root),
    }


def render_history(data: dict[str, Any]) -> None:
    print("HAL History")
    print("===========")
    print()
    sources = data.get("sources", {})
    if isinstance(sources, dict):
        print(f"mq-agent: {sources.get('mq_agent', '-')}")
        print(f"brain:    {sources.get('brain', '-')}")
        print()

    print("Stack score")
    print("-----------")
    stack_rows = data.get("stack_score", [])
    if stack_rows:
        for item in stack_rows:
            print(f"{item['date']}  {item['score']}/100  {item['source']}")
    else:
        print("No stack score history found.")
    print()

    print("Brain growth")
    print("------------")
    growth_rows = data.get("brain_growth", [])
    if growth_rows:
        for item in growth_rows:
            print(f"{item['date']}  +{item['files']} files")
    else:
        print("No brain growth history found.")
    print()

    print("Release history")
    print("---------------")
    release_rows = data.get("release_history", [])
    if release_rows:
        for item in release_rows:
            print(f"{item['date']}  {item['path']}")
    else:
        print("No release history found.")


def collect_alerts(sample: bool = False) -> dict[str, Any]:
    data = dashboard_control.collect_dashboard(sample=sample)
    return {
        "title": "HAL Alerts",
        "alerts": data.get("alerts", []),
        "source": "dashboard",
    }


def render_alerts(data: dict[str, Any]) -> None:
    print("HAL Alerts")
    print("==========")
    print()
    alerts = data.get("alerts", [])
    if not alerts:
        print("No alerts.")
        return
    for alert in alerts:
        print(f"- {alert}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal history",
        description="Show stack score, brain growth, and release history.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--mq-agent-root", help="Override ~/.mq-agent source")
    parser.add_argument("--brain-root", help="Override mqobsidian source")
    parser.add_argument(
        "--alerts",
        action="store_true",
        help="Render alerts instead of history; used by mq-hal alerts.",
    )
    args = parser.parse_args(argv)

    if args.alerts:
        data = collect_alerts(sample=args.sample)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            render_alerts(data)
        return 0

    data = SAMPLE if args.sample else collect_history(
        Path(args.mq_agent_root).expanduser() if args.mq_agent_root else None,
        Path(args.brain_root).expanduser() if args.brain_root else None,
    )
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_history(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
