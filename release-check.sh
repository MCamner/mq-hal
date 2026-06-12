#!/usr/bin/env bash
# Release readiness check for mq-hal.
# Run from the repository root before every release.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      ;;
    *)
      echo "usage: ./release-check.sh [--dry-run]" >&2
      exit 2
      ;;
  esac
done

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
python3 -m py_compile mq_hal/tools/registry.py
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
python3 -m py_compile hal/stack.py
python3 -m py_compile hal/status.py
python3 -m py_compile hal/doctor.py
python3 -m py_compile hal/brain.py
python3 -m py_compile hal/release.py
python3 -m py_compile scripts/memory_status.py
python3 -m py_compile scripts/repo_memory.py
python3 -m py_compile scripts/agent_brief.py
python3 -m py_compile scripts/hello.py
python3 -m py_compile scripts/model_profiles.py
python3 -m py_compile scripts/model_status.py
python3 -m py_compile scripts/model_test.py
python3 -m py_compile scripts/version.py
python3 -m py_compile scripts/config_check.py
python3 -m py_compile scripts/update.py
python3 -m py_compile scripts/visual_hal.py
python3 -m py_compile scripts/tools_list.py
python3 -m py_compile scripts/models_list.py
python3 -m py_compile scripts/planner.py
python3 -m py_compile scripts/critic.py
python3 -m py_compile scripts/executor.py
python3 -m py_compile scripts/learn.py
python3 -m py_compile scripts/env_status.py
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

step "GitHub release tag"
if command -v gh &>/dev/null 2>&1; then
  if gh release view "v${VERSION}" &>/dev/null 2>&1; then
    fail "GitHub release v${VERSION} already exists — bump VERSION before releasing"
  else
    pass "v${VERSION} not yet released on GitHub"
  fi
else
  printf "\033[1;33m[SKIP]\033[0m gh CLI not available — skipping GitHub release check\n"
fi

step "Smoke tests"
_smoke_start=$FAILED
./tests/smoke.sh                          || fail "smoke.sh"
./tests/doctor-summary-smoke.sh           || fail "doctor-summary-smoke.sh"
./tests/fix-planner-smoke.sh              || fail "fix-planner-smoke.sh"
./tests/session-memory-smoke.sh           || fail "session-memory-smoke.sh"
./tests/timeline-smoke.sh                 || fail "timeline-smoke.sh"
./tests/brief-smoke.sh                    || fail "brief-smoke.sh"
./tests/repo-status-smoke.sh              || fail "repo-status-smoke.sh"
./tests/ci-status-smoke.sh                || fail "ci-status-smoke.sh"
./tests/release-brief-smoke.sh            || fail "release-brief-smoke.sh"
./tests/release-control-smoke.sh          || fail "release-control-smoke.sh"
./tests/audit-smoke.sh                    || fail "audit-smoke.sh"
./tests/stack-status-smoke.sh             || fail "stack-status-smoke.sh"
./tests/hal-router-smoke.sh               || fail "hal-router-smoke.sh"
./tests/intent-schema-smoke.sh            || fail "intent-schema-smoke.sh"
./tests/router-safety-smoke.sh            || fail "router-safety-smoke.sh — safety gate failed"
./tests/memory-status-smoke.sh            || fail "memory-status-smoke.sh"
./tests/brain-smoke.sh                    || fail "brain-smoke.sh"
./tests/repo-memory-smoke.sh              || fail "repo-memory-smoke.sh"
./tests/agent-brief-smoke.sh              || fail "agent-brief-smoke.sh"
./tests/hello-smoke.sh                    || fail "hello-smoke.sh"
./tests/tools-smoke.sh                    || fail "tools-smoke.sh"
./tests/models-smoke.sh                   || fail "models-smoke.sh"
./tests/model-status-smoke.sh             || fail "model-status-smoke.sh"
./tests/model-test-smoke.sh               || fail "model-test-smoke.sh"
./tests/install-flow-smoke.sh             || fail "install-flow-smoke.sh"
./tests/visual-hal-smoke.sh               || fail "visual-hal-smoke.sh"
./tests/prompt-regression-smoke.sh        || fail "prompt-regression-smoke.sh"
./tests/plan-smoke.sh                     || fail "plan-smoke.sh"
./tests/critic-smoke.sh                   || fail "critic-smoke.sh"
./tests/execute-smoke.sh                  || fail "execute-smoke.sh"
./tests/learn-smoke.sh                    || fail "learn-smoke.sh"
./tests/env-status-smoke.sh               || fail "env-status-smoke.sh"
./tests/docs-smoke.sh                     || fail "docs-smoke.sh"
[[ "$FAILED" -eq "$_smoke_start" ]] && pass "all smoke tests passed"

step "Command surface consistency"
./tools/check-command-docs.sh
pass "command surface consistent"

printf '\n'
if [[ "$FAILED" -eq 0 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf "\033[1;32m=== release-check dry-run passed — v%s checks are green ===\033[0m\n" "$VERSION"
  else
    printf "\033[1;32m=== release-check passed — ready for v%s ===\033[0m\n" "$VERSION"
  fi
else
  printf "\033[1;31m=== release-check FAILED — fix issues before releasing ===\033[0m\n"
  exit 1
fi
