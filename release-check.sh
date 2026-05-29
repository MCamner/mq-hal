#!/usr/bin/env bash
# Release readiness check for mq-hal.
# Run from the repository root before every release.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

pass() { printf "\033[1;32m[PASS]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[FAIL]\033[0m %s\n" "$*" >&2; FAILED=1; }
step() { printf "\033[1;34m[----]\033[0m %s\n" "$*"; }

FAILED=0
VERSION="$(cat VERSION)"

step "Intent contract"
test -f "schemas/intent.schema.json" \
  || { fail "schemas/intent.schema.json missing"; }
test -f "docs/INTENT_CONTRACT.md" \
  || { fail "docs/INTENT_CONTRACT.md missing"; }
test -f "docs/COMMAND_SURFACE.md" \
  || { fail "docs/COMMAND_SURFACE.md missing"; }
python3 - <<'EOF' || { fail "intent schema version or enum mismatch"; }
import sys, json
sys.path.insert(0, "scripts")
import hal
schema = json.load(open("schemas/intent.schema.json"))
const = schema["properties"]["schema"]["const"]
assert const == hal.INTENT_SCHEMA_VERSION, \
    f"schema const {const!r} != INTENT_SCHEMA_VERSION {hal.INTENT_SCHEMA_VERSION!r}"
enum = set(schema["properties"]["intent"]["enum"])
assert enum == hal.ALLOWED_INTENTS, \
    f"schema enum differs from ALLOWED_INTENTS: {enum ^ hal.ALLOWED_INTENTS}"
EOF
pass "intent contract consistent"

step "Python syntax check"
python3 -m py_compile scripts/hal.py
python3 -m py_compile scripts/doctor_summary.py
python3 -m py_compile scripts/fix_planner.py
python3 -m py_compile scripts/session_memory.py
python3 -m py_compile scripts/timeline.py
python3 -m py_compile scripts/repo_status.py
python3 -m py_compile scripts/ci_status.py
python3 -m py_compile scripts/brief.py
python3 -m py_compile scripts/release_brief.py
python3 -m py_compile scripts/audit.py
python3 -m py_compile scripts/stack_status.py
python3 -m py_compile scripts/memory_status.py
python3 -m py_compile scripts/agent_brief.py
python3 -m py_compile tools/write_readme.py
python3 -m py_compile tools/markdown_guard.py
pass "Python syntax OK"

step "README markdown guard"
python3 tools/markdown_guard.py README.md && pass "README markdown guard" || fail "README markdown guard failed"

step "README contains version $VERSION"
grep -q "version-${VERSION}" README.md && pass "README badge references $VERSION" || fail "README badge does not reference $VERSION"

step "CHANGELOG contains version $VERSION"
grep -q "\[${VERSION}\]" CHANGELOG.md && pass "CHANGELOG references $VERSION" || fail "CHANGELOG does not reference $VERSION"

step "docs/index.html contains version $VERSION"
grep -q "v${VERSION}" docs/index.html && pass "docs/index.html references v$VERSION" || fail "docs/index.html does not reference v$VERSION"

step "Smoke tests"
./tests/smoke.sh
./tests/doctor-summary-smoke.sh
./tests/fix-planner-smoke.sh
./tests/session-memory-smoke.sh
./tests/timeline-smoke.sh
./tests/brief-smoke.sh
./tests/repo-status-smoke.sh
./tests/ci-status-smoke.sh
./tests/release-brief-smoke.sh
./tests/audit-smoke.sh
./tests/stack-status-smoke.sh
./tests/hal-router-smoke.sh
./tests/intent-schema-smoke.sh
./tests/router-safety-smoke.sh
./tests/memory-status-smoke.sh
./tests/agent-brief-smoke.sh
./tests/docs-smoke.sh
pass "all smoke tests passed"

step "Command surface consistency"
./tools/check-command-docs.sh
pass "command surface consistent"

printf '\n'
if [[ "$FAILED" -eq 0 ]]; then
  printf "\033[1;32m=== release-check passed — ready for v%s ===\033[0m\n" "$VERSION"
else
  printf "\033[1;31m=== release-check FAILED — fix issues before releasing ===\033[0m\n"
  exit 1
fi
