#!/usr/bin/env python3
"""Runtime control view for local MQ services."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MQ_MCP_URL = os.environ.get("MQ_MCP_URL", "http://localhost:8765").rstrip("/")
BRAIN_ROOT = Path(
    os.environ.get("MQ_HAL_BRAIN_ROOT")
    or os.environ.get("MQOBSIDIAN_PATH")
    or str(Path.home() / "mqobsidian")
).expanduser()


SAMPLE_RUNTIME: dict[str, Any] = {
    "title": "MQ Runtime",
    "services": [
        {
            "name": "Ollama",
            "status": "RUNNING",
            "detail": "http://localhost:11434/api/tags reachable",
            "checks": [{"name": "api", "status": "RUNNING"}],
        },
        {
            "name": "mq-mcp",
            "status": "RUNNING",
            "detail": "http://localhost:8765/tools reachable, 76 tools",
            "checks": [{"name": "tools", "status": "RUNNING", "tool_count": 76}],
        },
        {
            "name": "GitHub",
            "status": "WARN",
            "detail": "gh found, auth status unavailable",
            "checks": [{"name": "gh", "status": "RUNNING"}, {"name": "auth", "status": "WARN"}],
        },
        {
            "name": "brain",
            "status": "RUNNING",
            "detail": "~/mqobsidian exists",
            "checks": [{"name": "vault", "status": "RUNNING"}],
        },
    ],
    "overall": {"status": "WARN", "running": 3, "warn": 1, "down": 0},
}


@dataclass(frozen=True)
class ProbeResult:
    status: str
    detail: str
    checks: list[dict[str, Any]]


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    statuses = [str(check.get("status", "DOWN")).upper() for check in checks]
    if any(status == "DOWN" for status in statuses):
        return "DOWN"
    if any(status == "WARN" for status in statuses):
        return "WARN"
    return "RUNNING"


def _http_json(url: str, timeout: float = 2.0) -> tuple[dict[str, Any] | None, str]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status < 200 or resp.status >= 300:
                return None, f"HTTP {resp.status}"
            try:
                parsed = json.loads(body or "{}")
            except json.JSONDecodeError:
                return {}, "reachable, non-JSON response"
            return parsed if isinstance(parsed, dict) else {}, "reachable"
    except urllib.error.URLError as exc:
        return None, str(getattr(exc, "reason", exc))
    except TimeoutError:
        return None, "timed out"
    except OSError as exc:
        return None, str(exc)


def _run(cmd: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except OSError as exc:
        return 1, "", str(exc)
    return int(result.returncode), (result.stdout or "").strip(), (result.stderr or "").strip()


def probe_ollama() -> ProbeResult:
    checks: list[dict[str, Any]] = []
    binary = shutil.which("ollama")
    checks.append({
        "name": "binary",
        "status": "RUNNING" if binary else "WARN",
        "detail": binary or "ollama binary not found",
    })

    data, message = _http_json(f"{OLLAMA_URL}/api/tags")
    api_status = "RUNNING" if data is not None else "DOWN"
    models = data.get("models") if isinstance(data, dict) else None
    checks.append({
        "name": "api",
        "status": api_status,
        "detail": f"{OLLAMA_URL}/api/tags {message}",
        "model_count": len(models) if isinstance(models, list) else 0,
    })
    status = _status_from_checks(checks)
    detail = checks[-1]["detail"]
    return ProbeResult(status=status, detail=detail, checks=checks)


def probe_mq_mcp() -> ProbeResult:
    data, message = _http_json(f"{MQ_MCP_URL}/tools")
    tools = data.get("tools") if isinstance(data, dict) else None
    tool_count = len(tools) if isinstance(tools, list) else 0
    status = "RUNNING" if data is not None else "DOWN"
    detail = f"{MQ_MCP_URL}/tools {message}"
    if tool_count:
        detail = f"{detail}, {tool_count} tools"
    return ProbeResult(
        status=status,
        detail=detail,
        checks=[{
            "name": "tools",
            "status": status,
            "detail": detail,
            "tool_count": tool_count,
        }],
    )


def probe_github() -> ProbeResult:
    checks: list[dict[str, Any]] = []
    gh = shutil.which("gh")
    checks.append({
        "name": "binary",
        "status": "RUNNING" if gh else "DOWN",
        "detail": gh or "gh binary not found",
    })
    if not gh:
        return ProbeResult(status="DOWN", detail="gh binary not found", checks=checks)

    code, _out, err = _run([gh, "auth", "status"], timeout=6.0)
    auth_status = "RUNNING" if code == 0 else "WARN"
    checks.append({
        "name": "auth",
        "status": auth_status,
        "detail": "authenticated" if code == 0 else (err or "gh auth status failed"),
    })
    return ProbeResult(status=_status_from_checks(checks), detail=checks[-1]["detail"], checks=checks)


def probe_brain() -> ProbeResult:
    checks: list[dict[str, Any]] = []
    exists = BRAIN_ROOT.exists() and BRAIN_ROOT.is_dir()
    checks.append({
        "name": "vault",
        "status": "RUNNING" if exists else "DOWN",
        "detail": str(BRAIN_ROOT) if exists else f"{BRAIN_ROOT} not found",
    })
    if exists:
        expected = ["memory", "learn", "truth", "reviews"]
        missing = [name for name in expected if not (BRAIN_ROOT / name).exists()]
        checks.append({
            "name": "folders",
            "status": "RUNNING" if not missing else "WARN",
            "detail": "expected folders present" if not missing else "missing: " + ", ".join(missing),
            "missing": missing,
        })
    return ProbeResult(status=_status_from_checks(checks), detail=checks[-1]["detail"], checks=checks)


def collect_runtime() -> dict[str, Any]:
    probes = [
        ("Ollama", probe_ollama()),
        ("mq-mcp", probe_mq_mcp()),
        ("GitHub", probe_github()),
        ("brain", probe_brain()),
    ]
    services = [
        {
            "name": name,
            "status": result.status,
            "detail": result.detail,
            "checks": result.checks,
        }
        for name, result in probes
    ]
    counts = {
        "running": sum(1 for service in services if service["status"] == "RUNNING"),
        "warn": sum(1 for service in services if service["status"] == "WARN"),
        "down": sum(1 for service in services if service["status"] == "DOWN"),
    }
    if counts["down"]:
        overall = "DOWN"
    elif counts["warn"]:
        overall = "WARN"
    else:
        overall = "RUNNING"
    return {
        "title": "MQ Runtime",
        "services": services,
        "overall": {"status": overall, **counts},
    }


def render_runtime(data: dict[str, Any], details: bool = False) -> None:
    print(str(data.get("title") or "MQ Runtime"))
    print()
    services = [s for s in data.get("services", []) if isinstance(s, dict)]
    width = max([len(str(s.get("name", ""))) for s in services] + [7])
    for service in services:
        name = str(service.get("name", "unknown"))
        status = str(service.get("status", "DOWN"))
        detail = str(service.get("detail", ""))
        print(f"{name:<{width}}  {status:<7}  {detail}")
        if details:
            for check in service.get("checks", []):
                if isinstance(check, dict):
                    print(
                        f"{'':<{width}}    - {check.get('name', 'check')}: "
                        f"{check.get('status', 'DOWN')} {check.get('detail', '')}"
                    )
    print()
    overall = data.get("overall", {})
    if isinstance(overall, dict):
        print(
            "Overall: "
            f"{overall.get('status', 'UNKNOWN')} "
            f"({overall.get('running', 0)} running, "
            f"{overall.get('warn', 0)} warn, "
            f"{overall.get('down', 0)} down)"
        )


def main(argv: list[str]) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="JSON output")
    common.add_argument("--sample", action="store_true", help="Use sample runtime data")
    common.add_argument("--details", action="store_true", help="Show individual checks")

    parser = argparse.ArgumentParser(
        prog="mq-hal runtime",
        description="Show local MQ runtime service health.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser(
        "services",
        parents=[common],
        help="Show runtime services with health checks",
    )
    args = parser.parse_args(argv)

    data = SAMPLE_RUNTIME if args.sample else collect_runtime()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    render_runtime(data, details=args.details or args.command == "services")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
