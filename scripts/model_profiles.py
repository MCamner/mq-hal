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


def profile_for_name(
    profile_name: str | None,
    *,
    default_profile: str,
) -> dict[str, str]:
    """Return a validated provider/model profile with safe environment overrides."""
    data = load_model_profiles()
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}

    selected = profile_name or default_profile
    raw = profiles.get(selected)
    if not isinstance(raw, dict):
        known = ", ".join(sorted(profiles)) or "(none)"
        raise ValueError(f"unknown model profile: {selected}. Known profiles: {known}")

    provider = str(raw.get("provider", "ollama")).strip().lower()
    if provider not in {"ollama", "openai"}:
        raise ValueError(f"model profile {selected!r} has unsupported provider: {provider}")

    model = str(raw.get("model", "")).strip()
    env_var = "OLLAMA_MODEL" if provider == "ollama" else "OPENAI_MODEL"
    model = os.environ.get(env_var, model).strip()
    if not model:
        raise ValueError(f"model profile {selected!r} has no model")

    return {
        "name": selected,
        "provider": provider,
        "model": model,
        "reasoning_effort": str(raw.get("reasoning_effort", "medium")),
    }


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

    profile = profile_for_name(profile_name, default_profile=default_profile)
    return profile["model"], profile["name"]
