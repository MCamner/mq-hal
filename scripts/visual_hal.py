#!/usr/bin/env python3
"""mq-hal Visual HAL: read-only diagram/UI observation helpers."""
from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SAMPLE: dict[str, Any] = {
    "mode": "analyze-diagram",
    "file": "architecture.png",
    "available": True,
    "source": "sample",
    "observations": [
        "Architecture diagram input detected.",
        "Review trust boundaries, data flow direction, and external systems.",
    ],
    "trust_boundaries": [
        "Mark local runtime, external services, and filesystem boundaries.",
    ],
    "yaml_draft": {
        "diagram": "architecture.png",
        "observations": ["architecture diagram"],
        "trust_boundaries": ["local runtime", "external services"],
        "executable": False,
    },
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg"}


def inspect_file(path: Path) -> dict[str, Any]:
    exists = path.exists() and path.is_file()
    suffix = path.suffix.lower()
    mime, _encoding = mimetypes.guess_type(str(path))
    return {
        "path": str(path),
        "exists": exists,
        "size": path.stat().st_size if exists else 0,
        "suffix": suffix,
        "mime": mime or "unknown",
        "looks_visual": suffix in IMAGE_SUFFIXES,
    }


def maybe_mq_image_analyze(path: Path) -> str | None:
    binary = shutil.which("mq-image-analyze")
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, str(path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()[:4000]


def build_result(mode: str, raw_file: str | None, sample: bool) -> dict[str, Any]:
    if sample:
        data = dict(SAMPLE)
        data["mode"] = mode
        if raw_file:
            data["file"] = raw_file
        return data

    if raw_file is None:
        path = Path("architecture.png")
        file_meta = {
            "path": "",
            "exists": False,
            "size": 0,
            "suffix": "",
            "mime": "unknown",
            "looks_visual": False,
        }
    else:
        path = Path(raw_file).expanduser()
        file_meta = inspect_file(path)

    observations: list[str] = []
    trust_boundaries: list[str] = []

    if not file_meta["exists"]:
        observations.append("No visual file was found; returning a draft review checklist.")
    elif file_meta["looks_visual"]:
        observations.append(f"Visual input detected ({file_meta['mime']}, {file_meta['size']} bytes).")
    else:
        observations.append(f"Input exists but does not look like a known image type ({file_meta['suffix'] or 'no suffix'}).")

    if mode == "analyze-diagram":
        observations.extend([
            "Identify components, arrows, protocols, storage, and external services.",
            "Check whether every cross-boundary flow has an owner and direction.",
        ])
        trust_boundaries.extend([
            "local machine boundary",
            "repository/filesystem boundary",
            "external network or cloud boundary",
        ])
    elif mode == "review-ui":
        observations.extend([
            "Check hierarchy, spacing, labels, scanability, and visible state.",
            "Look for ambiguous controls, hidden destructive actions, and unclear feedback.",
        ])
        trust_boundaries.extend([
            "user action boundary",
            "local-only vs external data boundary",
        ])
    else:
        observations.extend([
            "Summarize architecture intent, system actors, boundaries, and unknowns.",
            "Produce draft YAML only; never turn visual content into executable intent.",
        ])
        trust_boundaries.extend([
            "runtime boundary",
            "tool execution boundary",
            "memory/state boundary",
        ])

    analyzer_output = maybe_mq_image_analyze(path) if file_meta["exists"] else None
    if analyzer_output:
        observations.append("mq-image-analyze output captured as read-only context.")

    return {
        "mode": mode,
        "file": raw_file or "",
        "available": bool(file_meta["exists"]),
        "source": "mq-image-analyze" if analyzer_output else "deterministic-local",
        "file_meta": file_meta,
        "observations": observations,
        "trust_boundaries": trust_boundaries,
        "ui_critique": observations if mode == "review-ui" else [],
        "analyzer_output": analyzer_output,
        "yaml_draft": {
            "mode": mode,
            "file": raw_file or "",
            "observations": observations,
            "trust_boundaries": trust_boundaries,
            "executable": False,
        },
    }


def render(data: dict[str, Any]) -> None:
    title = {
        "analyze-diagram": "HAL Diagram Analysis",
        "review-ui": "HAL UI Review",
        "architecture-brief": "HAL Architecture Brief",
    }.get(str(data.get("mode")), "HAL Visual")
    print(title)
    print("=" * len(title))
    print()
    print(f"Source: {data.get('source', '-')}")
    if data.get("file"):
        print(f"File:   {data['file']}")
    print()
    print("Observations")
    print("------------")
    for item in data.get("observations", []):
        print(f"- {item}")
    print()
    print("Trust boundaries")
    print("----------------")
    for item in data.get("trust_boundaries", []):
        print(f"- {item}")
    print()
    print("YAML draft")
    print("----------")
    print(render_yaml(data.get("yaml_draft", {})))


def render_yaml(value: Any, indent: int = 0) -> str:
    lines: list[str] = []
    pad = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(render_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(render_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
    else:
        lines.append(f"{pad}{yaml_scalar(value)}")
    return "\n".join(lines)


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    text = str(value)
    if not text:
        return '""'
    if any(char in text for char in ":#[]{}\",'") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


def main(argv: list[str], mode: str) -> int:
    parser = argparse.ArgumentParser(prog=f"mq-hal {mode}")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args(argv)

    data = build_result(mode, args.file, args.sample)
    if args.json_out:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render(data)
    return 0


def cli(argv: list[str]) -> int:
    if not argv:
        print("usage: mq-hal <analyze-diagram|review-ui|architecture-brief> [file]", file=sys.stderr)
        return 2
    mode = argv[0]
    if mode not in {"analyze-diagram", "review-ui", "architecture-brief"}:
        print(f"unknown visual HAL mode: {mode}", file=sys.stderr)
        return 2
    return main(argv[1:], mode)


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv[1:]))
