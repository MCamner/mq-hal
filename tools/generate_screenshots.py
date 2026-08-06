#!/usr/bin/env python3
"""Render docs/screenshots/*.png from real mq-hal command output.

Runs each command, captures stdout, and draws it as an amber terminal frame.
Nothing is hand-written: if a command changes, re-run this and the screenshot
follows. Home paths are rewritten to ~ so the images carry no local paths.

Usage:
    uv venv .venv && uv pip install --python .venv/bin/python pillow
    .venv/bin/python tools/generate_screenshots.py

Do not run this through `uv run --with pillow`: that puts an ephemeral venv on
PATH, `shutil.which("mq-agent")` inside mq-hal then finds an mq-agent without
its dependencies, and every panel renders UNAVAILABLE.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "screenshots"

BG = (13, 13, 15)
CHROME = (24, 24, 28)
TEXT = (255, 176, 0)
DIM = (138, 96, 20)
PROMPT = (255, 214, 122)
HAL_RED = (214, 48, 48)

STATUS_COLORS = {
    "PASS": (86, 211, 100),
    "WARN": (233, 180, 48),
    "FAIL": HAL_RED,
    "UNAVAILABLE": HAL_RED,
    "SKIPPED": DIM,
}

FONT_CANDIDATES = [
    Path.home() / "Library/Fonts/JetBrainsMonoNerdFontMono-Regular.ttf",
    Path("/System/Library/Fonts/SFNSMono.ttf"),
    Path("/System/Library/Fonts/Supplemental/Andale Mono.ttf"),
]

FONT_SIZE = 15
LINE_H = 22
PADDING = 26
TITLE_H = 30


def _font(size: int = FONT_SIZE) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                continue
    return ImageFont.load_default()


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _scrub(text: str) -> str:
    """Drop local paths so a screenshot never ships someone's home directory."""
    return ANSI.sub("", text).replace(str(Path.home()), "~")


def _clean_env() -> dict[str, str]:
    """Leave any active virtualenv behind.

    mq-hal locates mq-agent with shutil.which. If an activated venv shadows it
    with a copy that lacks mq-agent's dependencies, the routing and stack
    panels render UNAVAILABLE and the screenshot documents the wrong thing.
    """
    env = dict(os.environ, NO_COLOR="1")
    venv = env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    if venv:
        bin_dir = str(Path(venv) / "bin")
        env["PATH"] = ":".join(p for p in env["PATH"].split(":") if p != bin_dir)
    return env


def run(cmd: list[str]) -> str:
    env = _clean_env()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
        timeout=120,
        env=env,
    )
    output = (result.stdout + result.stderr).strip()
    if not output:
        raise SystemExit(f"no output from: {' '.join(cmd)}")
    return _scrub(output)


def _line_color(line: str) -> tuple[int, int, int]:
    stripped = line.strip()
    if stripped.endswith("=") or stripped.endswith("-") and set(stripped) <= {"-", "="}:
        return DIM
    return TEXT


def _draw_line(draw: ImageDraw.ImageDraw, x: int, y: int, line: str, font) -> None:
    """Draw one line, colouring any mq.feedback.v1 status token it contains."""
    base = _line_color(line)
    parts = re.split(r"\b(PASS|WARN|FAIL|UNAVAILABLE|SKIPPED)\b", line)
    for part in parts:
        if not part:
            continue
        color = STATUS_COLORS.get(part, base)
        draw.text((x, y), part, font=font, fill=color)
        x += int(draw.textlength(part, font=font))


def render(filename: str, command: str, output: str) -> None:
    font = _font()
    chrome_font = _font(12)
    lines = output.splitlines()

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widest = max(
        [probe.textlength(f"$ {command}", font=font)]
        + [probe.textlength(line, font=font) for line in lines]
    )
    width = int(widest) + PADDING * 2
    height = TITLE_H + PADDING + (len(lines) + 2) * LINE_H + PADDING

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, TITLE_H], fill=CHROME)
    draw.ellipse([14, 10, 26, 22], fill=HAL_RED)
    draw.text((38, 8), "mq-hal", font=chrome_font, fill=DIM)

    y = TITLE_H + PADDING
    draw.text((PADDING, y), "$ ", font=font, fill=PROMPT)
    draw.text(
        (PADDING + int(draw.textlength("$ ", font=font)), y),
        command,
        font=font,
        fill=PROMPT,
    )
    y += LINE_H * 2

    for line in lines:
        _draw_line(draw, PADDING, y, line, font)
        y += LINE_H

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / filename)
    print(f"  {filename}  {width}x{height}")


SHOTS = [
    ("runtime.png", "mq-hal runtime", ["mq-hal", "runtime"]),
    ("route.png", "mq-hal route", ["mq-hal", "route"]),
    ("context.png", "mq-hal context", ["mq-hal", "context"]),
]


def main() -> None:
    print("Generating screenshots from live command output...")
    for filename, label, cmd in SHOTS:
        render(filename, label, run(cmd))
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
