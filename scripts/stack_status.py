#!/usr/bin/env python3
"""mq-hal stack-status: local stack overview for mq-hal + repo-signal."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "repos.json"

SAMPLE: dict[str, Any] = {
    "status": "ok",
    "tools": {
        "mq-hal": {"available": True, "path": "bin/mq-hal"},
        "mqlaunch": {"available": True, "path": "/usr/local/bin/mqlaunch"},
        "repo-signal": {
            "available": True,
            "path": "/opt/homebrew/bin/repo-signal",
        },
        "mq-agent": {
            "available": True,
            "path": "~/.local/bin/mq-agent",
        },
        "bridget": {"available": True, "path": "~/bin/bridget"},
    },
    "mq_mcp": {
        "available": True,
        "path": "~/mq-mcp",
        "version": "1.9.0",
        "runtime": "ok",
        "vector": "ok",
        "model": "configured",
        "http_reachable": True,
        "tool_count": 76,
        "has_orchestration_contract": True,
        "has_learn_tools": True,
        "has_review_skills": True,
    },
    "repos": [
        {
            "name": "macos-scripts",
            "path": "~/macos-scripts",
            "exists": True,
            "branch": "main",
            "dirty": False,
            "version": "0.4.11",
            "publish": {"available": True, "score": 16, "total": 16, "status": "ready"},
        },
        {
            "name": "repo-signal",
            "path": "~/repo-signal",
            "exists": True,
            "branch": "main",
            "dirty": False,
            "version": "0.3.0",
            "publish": {"available": True, "score": 16, "total": 16, "status": "ready"},
        },
        {
            "name": "mq-mcp",
            "path": "~/mq-mcp",
            "exists": True,
            "branch": "main",
            "dirty": False,
            "version": "0.2.0",
            "publish": {"available": True, "score": 15, "total": 16, "status": "needs_review"},
        },
    ],
    "recommendation": "Stack looks usable. Next: add mqlaunch menu bridge for stack-status.",
}


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.stdout or "").strip(), int(result.returncode)
    except FileNotFoundError:
        return "", 127
    except subprocess.TimeoutExpired:
        return "", 124
    except OSError:
        return "", 1


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "default_repo": "macos-scripts",
            "repos": {
                "macos-scripts": "~/macos-scripts",
                "repo-signal": "~/repo-signal",
                "mq-mcp": "~/mq-mcp",
            },
        }

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"default_repo": "macos-scripts", "repos": {}}

    if not isinstance(data, dict):
        return {"default_repo": "macos-scripts", "repos": {}}

    if not isinstance(data.get("repos"), dict):
        data["repos"] = {}

    return data


def read_version(repo_path: Path) -> str:
    for candidate in (repo_path / "VERSION", repo_path / "version.txt"):
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8").strip()
            except OSError:
                return "-"
    return "-"


def collect_publish(repo_path: Path) -> dict[str, Any]:
    if shutil.which("repo-signal") is None:
        return {"available": False, "score": 0, "total": 0, "status": "repo-signal unavailable"}

    out, code = run(
        ["repo-signal", "publish-checklist", str(repo_path), "--format", "json"],
        timeout=40,
    )
    if not out or code != 0:
        return {"available": False, "score": 0, "total": 0, "status": "unavailable"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"available": False, "score": 0, "total": 0, "status": "parse_error"}

    return {
        "available": True,
        "score": int(data.get("score", 0)),
        "total": int(data.get("total", 0)),
        "status": str(data.get("status", "unknown")),
    }


def collect_repo(name: str, raw_path: str) -> dict[str, Any]:
    repo_path = Path(raw_path).expanduser().resolve()
    exists = repo_path.exists() and repo_path.is_dir()

    item: dict[str, Any] = {
        "name": name,
        "path": str(repo_path),
        "exists": exists,
        "branch": "-",
        "dirty": False,
        "version": "-",
        "publish": {"available": False, "score": 0, "total": 0, "status": "not_checked"},
    }

    if not exists:
        item["publish"]["status"] = "repo_missing"
        return item

    branch, _ = run(["git", "branch", "--show-current"], cwd=repo_path)
    status, _ = run(["git", "status", "--porcelain"], cwd=repo_path)

    item["branch"] = branch or "-"
    item["dirty"] = bool(status.strip())
    item["version"] = read_version(repo_path)
    item["publish"] = collect_publish(repo_path)
    return item


def _find_mq_agent() -> str | None:
    env = os.environ.get("MQ_AGENT_BIN")
    if env and Path(env).expanduser().exists():
        return str(Path(env).expanduser())
    w = shutil.which("mq-agent")
    if w:
        return w
    for candidate in (
        Path.home() / ".local" / "bin" / "mq-agent",
        Path.home() / "mq-agent" / ".venv" / "bin" / "mq-agent",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def collect_tools() -> dict[str, dict[str, Any]]:
    local_bin = BASE_DIR / "bin" / "mq-hal"
    mq_agent = _find_mq_agent()
    return {
        "mq-hal": {
            "available": local_bin.exists(),
            "path": str(local_bin),
        },
        "mqlaunch": {
            "available": shutil.which("mqlaunch") is not None,
            "path": shutil.which("mqlaunch") or "",
        },
        "repo-signal": {
            "available": shutil.which("repo-signal") is not None,
            "path": shutil.which("repo-signal") or "",
        },
        "mq-agent": {
            "available": mq_agent is not None,
            "path": mq_agent or "",
        },
        "bridget": {
            "available": shutil.which("bridget") is not None,
            "path": shutil.which("bridget") or "",
        },
    }


def _repo_path(config: dict[str, Any], name: str) -> Path | None:
    repos = config.get("repos", {})
    if isinstance(repos, dict) and name in repos:
        return Path(str(repos[name])).expanduser().resolve()
    return None


def _probe_mq_mcp_http(endpoint: str = "http://localhost:8765") -> dict[str, Any]:
    """Try GET {endpoint}/tools. Returns tool count and feature flags. Never raises."""
    import urllib.error
    import urllib.request

    out: dict[str, Any] = {
        "reachable": False,
        "tool_count": 0,
        "has_orchestration_contract": False,
        "has_learn_tools": False,
        "has_review_skills": False,
    }
    try:
        req = urllib.request.Request(
            f"{endpoint}/tools",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                raw = data.get("tools", [])
                names = {
                    item["name"] if isinstance(item, dict) else str(item)
                    for item in raw
                }
                out["reachable"] = True
                out["tool_count"] = len(names)
                out["has_orchestration_contract"] = "validate_orchestration_contract" in names
                out["has_learn_tools"] = bool({"learn_status", "search_learned_patterns"} & names)
                out["has_review_skills"] = bool({"list_review_skills", "review_file"} & names)
    except Exception:
        pass
    return out


def collect_mq_mcp(config: dict[str, Any]) -> dict[str, Any]:
    repo_path = _repo_path(config, "mq-mcp")
    if repo_path is None:
        return {
            "available": False,
            "path": "",
            "version": "-",
            "runtime": "not_configured",
            "vector": "unknown",
            "model": "unknown",
        }

    exists = repo_path.exists() and repo_path.is_dir()
    version = read_version(repo_path) if exists else "-"
    server_candidates = [
        repo_path / "server.py",
        repo_path / "mq-mcp" / "server.py",
        repo_path / "mq_mcp" / "server.py",
    ]
    runtime = "ok" if exists and any(path.exists() for path in server_candidates) else "missing-runtime"

    semantic_dir = repo_path / "semantic_memory"
    vector_files = [
        semantic_dir / "store.json",
        semantic_dir / "schema.json",
        repo_path / "vector_store.json",
    ]
    vector = "ok" if exists and any(path.exists() for path in vector_files) else "missing-vector-store"

    profiles_dir = repo_path / "profiles"
    env_model = os.environ.get("OPENAI_API_KEY") or os.environ.get("OLLAMA_MODEL")
    model = "configured" if env_model or (exists and profiles_dir.exists()) else "unknown"

    http = _probe_mq_mcp_http()
    return {
        "available": exists,
        "path": str(repo_path),
        "version": version,
        "runtime": runtime,
        "vector": vector,
        "model": model,
        "http_reachable": http["reachable"],
        "tool_count": http["tool_count"],
        "has_orchestration_contract": http["has_orchestration_contract"],
        "has_learn_tools": http["has_learn_tools"],
        "has_review_skills": http["has_review_skills"],
    }


def derive_status(data: dict[str, Any]) -> str:
    tools = data["tools"]
    repos = data["repos"]

    if not tools["mq-hal"]["available"]:
        return "not_ready"
    if any(not repo["exists"] for repo in repos):
        return "needs_review"
    if not tools["repo-signal"]["available"]:
        return "needs_review"
    mq_mcp = data.get("mq_mcp", {})
    if isinstance(mq_mcp, dict) and mq_mcp.get("available") and mq_mcp.get("runtime") != "ok":
        return "needs_review"
    if any(repo["dirty"] for repo in repos):
        return "needs_review"
    return "ok"


def derive_recommendation(data: dict[str, Any]) -> str:
    tools = data["tools"]
    repos = data["repos"]

    missing_tools = [name for name, meta in tools.items() if not meta["available"]]
    missing_repos = [repo["name"] for repo in repos if not repo["exists"]]
    dirty_repos = [repo["name"] for repo in repos if repo["dirty"]]

    if missing_repos:
        return "Fix missing configured repos: " + ", ".join(missing_repos) + "."
    if "repo-signal" in missing_tools:
        return "Install or link repo-signal so HAL Audit and Stack Status can score repo quality."
    if dirty_repos:
        return "Review dirty repos before release work: " + ", ".join(dirty_repos) + "."
    if "mqlaunch" in missing_tools:
        return "mq-hal works, but mqlaunch is not on PATH. Link mqlaunch before adding menu integration."
    mq_mcp = data.get("mq_mcp", {})
    if isinstance(mq_mcp, dict) and mq_mcp.get("available") and mq_mcp.get("vector") != "ok":
        return "mq-mcp is present, but vector/semantic memory looks incomplete."
    if isinstance(mq_mcp, dict) and mq_mcp.get("available") and not mq_mcp.get("http_reachable"):
        return "mq-mcp is installed but not reachable. Start it with: mq-agent mcp start"
    if "bridget" in missing_tools:
        return "Core stack works. Optional: link bridget globally if you want terminal chat from anywhere."
    return "Stack looks usable. Next: add mqlaunch menu bridge for stack-status."


def collect() -> dict[str, Any]:
    config = load_config()
    repos_cfg = config.get("repos", {})
    repos = [collect_repo(str(name), str(path)) for name, path in sorted(repos_cfg.items())]

    data: dict[str, Any] = {
        "status": "unknown",
        "tools": collect_tools(),
        "mq_mcp": collect_mq_mcp(config),
        "repos": repos,
        "recommendation": "",
    }
    data["status"] = derive_status(data)
    data["recommendation"] = derive_recommendation(data)
    return data


def render(data: dict[str, Any]) -> None:
    print("HAL Stack Status")
    print("================")
    print()
    print(f"Status: {data['status']}")
    print()

    print("Tools")
    print("-----")
    for name, meta in data["tools"].items():
        marker = "OK" if meta["available"] else "MISS"
        path = meta["path"] or "-"
        print(f"{marker:<5} {name:<12} {path}")
    print()

    mq_mcp = data.get("mq_mcp", {})
    if isinstance(mq_mcp, dict):
        print("mq-mcp runtime")
        print("--------------")
        print(f"available={mq_mcp.get('available')} path={mq_mcp.get('path') or '-'}")
        print(
            f"version={mq_mcp.get('version', '-')} "
            f"runtime={mq_mcp.get('runtime', '-')} "
            f"vector={mq_mcp.get('vector', '-')} "
            f"model={mq_mcp.get('model', '-')}"
        )
        reachable = mq_mcp.get("http_reachable")
        if reachable is not None:
            tc = mq_mcp.get("tool_count", 0)
            oc = "yes" if mq_mcp.get("has_orchestration_contract") else "no"
            learn = "yes" if mq_mcp.get("has_learn_tools") else "no"
            review = "yes" if mq_mcp.get("has_review_skills") else "no"
            status = f"reachable tools={tc}" if reachable else "not reachable"
            print(
                f"http={status} "
                f"orchestration_contract={oc} "
                f"learn={learn} "
                f"review_skills={review}"
            )
        print()

    print("Configured repos")
    print("----------------")
    for repo in data["repos"]:
        exists = "OK" if repo["exists"] else "MISS"
        dirty = "dirty" if repo["dirty"] else "clean"
        publish = repo["publish"]
        if publish["available"]:
            score = f"{publish['score']}/{publish['total']} {publish['status']}"
        else:
            score = publish["status"]

        print(
            f"{exists:<5} {repo['name']:<16} "
            f"branch={repo['branch']:<10} "
            f"state={dirty:<6} "
            f"version={repo['version']:<8} "
            f"publish={score}"
        )

    print()
    print("Recommendation")
    print("--------------")
    print(data["recommendation"])
    print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="mq-hal stack-status",
        description="Show local stack status for mq-hal, repo-signal, mq-mcp, mqlaunch, and configured repos.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--sample", action="store_true", help="Print sample output without touching local repos.")
    args = parser.parse_args(argv)

    data = SAMPLE if args.sample else collect()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
