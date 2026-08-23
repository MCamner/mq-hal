#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR"' EXIT

export MQ_HAL_STATE_DIR="$STATE_DIR"
export PYTHONPYCACHEPREFIX="$STATE_DIR/pycache"

echo "SMOKE: critic"

echo "[1/8] syntax check"
python3 -m py_compile "$ROOT/scripts/critic.py"

echo "[2/8] sample critique works without external AI"
"$ROOT/bin/mq-hal" critic --sample --no-ai >/dev/null

echo "[3/8] sample output contains expected sections"
out="$("$ROOT/bin/mq-hal" critic --sample --no-ai)"
echo "$out" | grep -q "^HAL Critic"
echo "$out" | grep -q "Verdict:"
echo "$out" | grep -q "Checks"
echo "  sections found: OK"

echo "[4/8] sample --json produces valid JSON with expected keys"
python3 - <<EOF
import json, subprocess
r = subprocess.run(
    ["$ROOT/bin/mq-hal", "critic", "--sample", "--no-ai", "--json"],
    capture_output=True, text=True,
)
assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
d = json.loads(r.stdout)
for key in ("goal", "risk", "verdict", "findings", "used_ai",
            "ai_advisory", "fail_count", "warn_count"):
    assert key in d, f"missing key: {key}"
assert d["verdict"] in ("pass", "review", "fail"), \
    f"invalid verdict: {d['verdict']}"
assert isinstance(d["findings"], list), "findings must be a list"
assert d["used_ai"] is False
assert d["ai_advisory"] is None
print(f"  verdict={d['verdict']}, {len(d['findings'])} findings: OK")
EOF

echo "[5/8] dangerous plan returns FAIL verdict"
python3 - <<EOF
import json, sys, os
sys.path.insert(0, '$ROOT/scripts')
import critic

bad_plan = {
    "goal": "delete everything",
    "affected_repos": [],
    "affected_files": [],
    "risk": "high",
    "steps": [
        {
            "id": 1,
            "description": "nuke",
            "safe_command": "rm -rf /",
            "requires_confirm": False,
        }
    ],
    "validation": [],
    "rollback_plan": None,
}
findings = critic.run_checks(bad_plan)
v = critic.verdict(findings)
assert v == "FAIL", f"Expected FAIL for dangerous plan, got {v}"
fail_checks = [f.check for f in findings if f.level == "fail"]
assert "dangerous-commands" in fail_checks, \
    f"Expected dangerous-commands finding, got {fail_checks}"
print(f"  dangerous plan → FAIL ({', '.join(fail_checks)}): OK")
EOF

echo "[6/8] clean plan returns PASS or REVIEW"
python3 - <<EOF
import json, sys
sys.path.insert(0, '$ROOT/scripts')
import critic

good_plan = {
    "goal": "bump version to 0.15.0",
    "affected_repos": ["mq-hal"],
    "affected_files": ["VERSION", "CHANGELOG.md"],
    "risk": "low",
    "steps": [
        {
            "id": 1,
            "description": "check current version",
            "safe_command": "cat VERSION",
            "requires_confirm": False,
        },
        {
            "id": 2,
            "description": "update VERSION file",
            "safe_command": None,
            "requires_confirm": True,
        },
    ],
    "validation": ["release-check.sh passes"],
    "rollback_plan": "git restore VERSION CHANGELOG.md",
}
findings = critic.run_checks(good_plan)
v = critic.verdict(findings)
assert v in ("PASS", "REVIEW"), f"Expected PASS/REVIEW for clean plan, got {v}"
print(f"  clean plan → {v}: OK")
EOF

echo "[7/8] AI advisory uses critic profile and remains non-authoritative"
python3 - <<EOF
import json, sys
from unittest.mock import patch
sys.path.insert(0, '$ROOT/scripts')
import critic

raw = json.dumps({
    "summary": "Plan needs human review.",
    "concerns": ["Check the rollback assumption."],
    "recommendations": ["Run the deterministic validation first."],
})
with patch.object(critic, "generate_structured", return_value=raw) as generate:
    advisory = critic.ai_advisory(critic.SAMPLE_PLAN, "critic")
assert advisory is not None
assert advisory["summary"] == "Plan needs human review."
assert generate.call_args.kwargs["model"] == "gpt-5.4-mini"
assert generate.call_args.kwargs["reasoning_effort"] == "high"
print("  critic profile advisory: OK")
EOF

echo "[8/8] code-plan routes through the code profile without execution"
out="$("$ROOT/bin/mq-hal" code-plan --no-ai --json "inspect a Python change")"
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["risk"]=="unknown"' <<<"$out"
echo "  code-plan command: OK"

echo "OK: critic smoke test passed"
