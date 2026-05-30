#!/usr/bin/env python3
"""Shared mq-hal model profile helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_PATH = BASE_DIR / "config" / "models.json"


def load_model_profiles() -> dict[str, Any]:
    try:
        data = json.loads(MODELS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}, "default": "router"}
    return data if isinstance(data, dict) else {"profiles": {}, "default": "router"}


def model_for_profile(
    profile_name: str | None,
    *,
    default_profile: str,
    env_var: str = "OLLAMA_MODEL",
    env_default: str,
) -> tuple[str, str]:
    """Return (model, profile) for a named profile, with env override support."""
    env_model = os.environ.get(env_var)
    if env_model:
        return env_model, f"{env_var}"

    data = load_model_profiles()
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}

    selected = profile_name or default_profile
    profile = profiles.get(selected)
    if not isinstance(profile, dict):
        known = ", ".join(sorted(profiles)) or "(none)"
        raise ValueError(f"unknown model profile: {selected}. Known profiles: {known}")

    model = profile.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"model profile {selected!r} has no model")

    return model.strip(), selected
