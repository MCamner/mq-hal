#!/usr/bin/env bash
# Shared provider projection plus real audit/canonical/legacy entrypoint behavior.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m unittest discover -s tests -p test_verification_status.py
