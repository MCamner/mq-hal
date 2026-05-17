#!/usr/bin/env python3
"""mq-hal audit — publish quality and README quality via repo-signal."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from session_memory import append_event  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE: dict[str, Any] = {
    "repo": "macos-scripts",
    "version": "0.3.9",
    "overall": "needs_review",
    "publish": {
        "available": True,
        "score": 15,
        "total": 16,
        "status": "needs_review",
        "checks": [
            {"group": "Front door", "name": "README exists", "status": "ok", "hint": ""},
            {"group": "Front door", "name": "README has quick start", "status": "ok", "hint": ""},
            {"group": "Front door", "name": "README links to GitHub Pages", "status": "ok", "hint": ""},
            {"group": "Front door", "name": "README mentions demo", "status": "ok", "hint": ""},
            {"group": "Front door", "name": "README mentions screenshots or gallery", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "LICENSE exists", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "CHANGELOG exists", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "VERSION exists", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": ".gitignore exists", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "README mentions roadmap", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "README mentions safe sharing/security", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "issue templates exist", "status": "ok", "hint": ""},
            {"group": "Public quality", "name": "roadmap file exists", "status": "warn", "hint": "Add ROADMAP.md"},
            {"group": "GitHub Pages", "name": "docs folder exists", "status": "ok", "hint": ""},
            {"group": "GitHub Pages", "name": "GitHub Pages landing exists", "status": "ok", "hint": ""},
            {"group": "GitHub Pages", "name": "docs screenshots folder exists", "status": "ok", "hint": ""},
        ],
    },
    "readme": {
        "available": True,
        "score": 50,
        "total": 100,
        "checks": [
            {"status": "ok", "name": "title"},
            {"status": "ok", "name": "short pitch"},
            {"status": "missing", "name": "install section"},
            {"status": "missing", "name": "usage section"},
            {"status": "missing", "name": "examples"},
            {"status": "ok", "name": "screenshots/demo"},
            {"status": "ok", "name": "badges"},
            {"status": "ok", "name": "license"},
            {"status": "missing", "name": "roadmap"},
            {"status": "missing", "name": "contributing"},
        ],
        "missing": ["install section", "usage section", "examples", "roadmap", "contributing"],
    },
    "recommendation": "README score is low (50/100). Add install, usage, and examples sections. Rerun audit when done.",
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"default_repo": "macos-scripts", "repos": {"macos-scripts": "~/macos-scripts"}}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"default_repo": "macos-scripts", "repos": {}}


def resolve_repo(repo_name: str | None) -> tuple[str, Path]:
    config = load_config()
    repos = config.get("repos", {})
    name = repo_name or str(config.get("default_repo") or "macos-scripts")
    if name not in repos:
        known = ", ".join(sorted(str(k) for k in repos))
        print(f"ERROR: unknown repo '{name}'. Known: {known}", file=sys.stderr)
        raise SystemExit(2)
    path = Path(str(repos[name])).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: repo '{name}' not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    return name, path


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
        )
        return (result.stdout or "").strip(), result.returncode
    except FileNotFoundError:
        return "", 127
    except subprocess.TimeoutExpired:
        return "", 124
    except OSError:
        return "", 1


def collect_version(repo_path: Path) -> str:
    for candidate in [repo_path / "VERSION", repo_path / "version.txt"]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return "-"


def collect_publish(repo_path: Path) -> dict[str, Any]:
    out, code = _run(["repo-signal", "publish-checklist", str(repo_path), "--format", "json"])
    if not out or code == 127:
        return {"available": False, "score": 0, "total": 0, "status": "unavailable", "checks": []}
    try:
        data = json.loads(out)
        score = int(data.get("score", 0))
        total = int(data.get("total", 1))
        status = str(data.get("status", "unknown"))
        checks = [
            {
                "group": str(c.get("group", "")),
                "name": str(c.get("name", "")),
                "status": str(c.get("status", "unknown")),
                "hint": str(c.get("hint", "")),
            }
            for c in (data.get("checks") or [])
        ]
        return {"available": True, "score": score, "total": total, "status": status, "checks": checks}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {"available": False, "score": 0, "total": 0, "status": "parse_error", "checks": []}


def collect_readme(repo_path: Path) -> dict[str, Any]:
    out, code = _run(["repo-signal", "readme-score", str(repo_path)])
    if not out or code == 127:
        return {"available": False, "score": 0, "total": 100, "checks": [], "missing": []}

    score, total = 0, 100
    m = re.search(r"README score:\s*(\d+)/(\d+)", out)
    if m:
        score, total = int(m.group(1)), int(m.group(2))

    checks: list[dict[str, str]] = []
    for item in re.finditer(r"-\s+\[(OK|MISSING)\]\s+(.+)", out):
        status = "ok" if item.group(1) == "OK" else "missing"
        checks.append({"status": status, "name": item.group(2).strip()})

    missing: list[str] = []
    miss_m = re.search(r"^Missing:\s+(.+)$", out, re.MULTILINE)
    if miss_m:
        missing = [s.strip() for s in miss_m.group(1).split(",") if s.strip()]

    return {"available": True, "score": score, "total": total, "checks": checks, "missing": missing}


def derive_overall(publish: dict[str, Any], readme: dict[str, Any]) -> str:
    if not publish["available"] and not readme["available"]:
        return "unavailable"
    p_ok = publish["available"] and publish["score"] >= publish["total"]
    r_ok = readme["available"] and readme["score"] >= 80
    if p_ok and r_ok:
        return "ready"
    if publish["available"] and publish["score"] < publish["total"] * 0.75:
        return "not_ready"
    return "needs_review"


def derive_recommendation(
    publish: dict[str, Any],
    readme: dict[str, Any],
    overall: str,
) -> str:
    parts: list[str] = []

    if not publish["available"] and not readme["available"]:
        return "repo-signal not found or not installed. Install it with: pip install repo-signal"

    if publish["available"] and publish["score"] < publish["total"]:
        failing = [c["name"] for c in publish["checks"] if c["status"] not in ("ok",)]
        if failing:
            parts.append(f"Fix publish checklist: {', '.join(failing[:3])}.")

    if readme["available"] and readme["missing"]:
        parts.append(f"Add README sections: {', '.join(readme['missing'][:4])}.")

    if overall == "ready":
        return "Repo looks publish-ready. Run mqlaunch release-check when ready to tag."
    if parts:
        return " ".join(parts) + " Then rerun mqlaunch hal audit."
    return "Review findings above and rerun mqlaunch hal audit."


def render(data: dict[str, Any]) -> None:
    publish = data["publish"]
    readme = data["readme"]

    print("HAL Audit")
    print("=========")
    print()
    print(f"Repo:    {data['repo']}")
    print(f"Version: {data['version']}")
    print(f"Overall: {data['overall']}")
    print()

    # Publish checklist
    if publish["available"]:
        p_pct = f"{publish['score']}/{publish['total']}"
        print(f"Publish readiness: {p_pct}")
        failing = [c for c in publish["checks"] if c["status"] not in ("ok",)]
        if failing:
            print("  Findings:")
            for c in failing[:6]:
                hint = f" — {c['hint']}" if c.get("hint") else ""
                print(f"  - [{c['status'].upper():<4}] {c['name']}{hint}")
    else:
        print("Publish readiness: unavailable (repo-signal not found)")
    print()

    # README score
    if readme["available"]:
        print(f"README score:      {readme['score']}/{readme['total']}")
        if readme["missing"]:
            print(f"  Missing: {', '.join(readme['missing'])}")
    else:
        print("README score:      unavailable (repo-signal not found)")
    print()

    # Recommendation
    print("Recommendation")
    print("--------------")
    print(data["recommendation"])
    print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal audit",
        description="Publish quality and README quality audit via repo-signal.",
    )
    parser.add_argument("--repo", help="Configured repo name. Defaults to config default_repo.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--sample", action="store_true", help="Print sample output without touching the repo.")
    parser.add_argument("--no-memory", action="store_true", help="Do not save to session memory.")
    args = parser.parse_args(argv)

    if args.sample:
        data: dict[str, Any] = SAMPLE
    else:
        repo_name, repo_path = resolve_repo(args.repo)
        version = collect_version(repo_path)
        publish = collect_publish(repo_path)
        readme = collect_readme(repo_path)
        overall = derive_overall(publish, readme)
        recommendation = derive_recommendation(publish, readme, overall)
        data = {
            "repo": repo_name,
            "version": version,
            "overall": overall,
            "publish": publish,
            "readme": readme,
            "recommendation": recommendation,
        }

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)

    if not args.sample and not args.no_memory and os.environ.get("MQ_HAL_DISABLE_MEMORY") != "1":
        append_event(
            "audit",
            payload={
                "repo": str(data.get("repo") or ""),
                "overall": str(data.get("overall") or ""),
                "publish_score": data.get("publish", {}).get("score", 0),
                "readme_score": data.get("readme", {}).get("score", 0),
                "version": str(data.get("version") or ""),
            },
            repo=str(data.get("repo") or ""),
            source="deterministic",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
