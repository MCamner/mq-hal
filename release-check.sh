#!/usr/bin/env bash
# Release readiness check for mq-hal. Read-only.
#
# Human mode (no flags / --dry-run): prints [PASS]/[FAIL] per check, exits 1 on
#   any failure. --dry-run skips the GitHub "already released" lookup.
# Contract mode (--json): emits a repo_release_check.v1 object on stdout and
#   exits 0 (the `status` field carries the verdict). Consumed by mq-agent's
#   `stack release --all --preflight`. --json implies read-only and network-free
#   (the GitHub lookup is skipped), matching --dry-run.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

DRY_RUN=0
JSON=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --json) JSON=1 ;;
    *) echo "usage: ./release-check.sh [--dry-run] [--json]" >&2; exit 2 ;;
  esac
done
# --json is preflight mode: always read-only and network-free.
[[ "$JSON" -eq 1 ]] && DRY_RUN=1

FAILED=0
BLOCKERS=()
VERSION="$(cat VERSION)"

step() { [[ "$JSON" -eq 1 ]] || printf "\033[1;34m[----]\033[0m %s\n" "$*"; }
pass() { [[ "$JSON" -eq 1 ]] || printf "\033[1;32m[PASS]\033[0m %s\n" "$*"; }
skip() { [[ "$JSON" -eq 1 ]] || printf "\033[1;33m[SKIP]\033[0m %s\n" "$*"; }
fail() { FAILED=1; BLOCKERS+=("$1"); [[ "$JSON" -eq 1 ]] || printf "\033[1;31m[FAIL]\033[0m %s\n" "$*" >&2; }

step "Intent contract"
[[ -f schemas/intent.schema.json ]] || fail "schemas/intent.schema.json missing"
[[ -f docs/INTENT_CONTRACT.md ]] || fail "docs/INTENT_CONTRACT.md missing"
[[ -f docs/COMMAND_SURFACE.md ]] || fail "docs/COMMAND_SURFACE.md missing"
if python3 - >/dev/null 2>&1 <<'EOF'
import json
import sys
sys.path.insert(0, "scripts")
import hal
schema = json.load(open("schemas/intent.schema.json"))
assert schema["properties"]["schema"]["const"] == hal.INTENT_SCHEMA_VERSION
assert set(schema["properties"]["intent"]["enum"]) == hal.ALLOWED_INTENTS
EOF
then
  pass "intent contract consistent"
else
  fail "intent schema version or enum mismatch"
fi

step "Python syntax check"
_pyfiles=(
  scripts/hal.py mq_hal/tools/registry.py scripts/doctor_summary.py
  scripts/fix_planner.py scripts/session_memory.py scripts/timeline.py
  scripts/repo_status.py scripts/ci_status.py scripts/brief.py
  scripts/release_brief.py scripts/audit.py scripts/stack_status.py
  hal/stack.py hal/status.py hal/doctor.py hal/brain.py hal/context.py hal/route.py
  hal/release.py scripts/memory_status.py scripts/repo_memory.py
  scripts/agent_brief.py scripts/hello.py scripts/model_profiles.py
  scripts/openai_client.py
  scripts/model_status.py scripts/model_test.py scripts/version.py
  scripts/config_check.py scripts/update.py scripts/visual_hal.py
  scripts/tools_list.py scripts/models_list.py scripts/planner.py
  scripts/critic.py scripts/executor.py scripts/learn.py scripts/env_status.py
  tools/write_readme.py tools/markdown_guard.py
)
if (set -e; for f in "${_pyfiles[@]}"; do python3 -m py_compile "$f"; done) >/dev/null 2>&1; then
  pass "Python syntax OK"
else
  fail "Python syntax check failed"
fi

step "README markdown guard"
if python3 tools/markdown_guard.py README.md >/dev/null 2>&1; then
  pass "README markdown guard"
else
  fail "README markdown guard failed"
fi

step "README contains version $VERSION"
if grep -q "version-${VERSION}" README.md; then
  pass "README badge references $VERSION"
else
  fail "README badge does not reference $VERSION"
fi

step "CHANGELOG contains version $VERSION"
if grep -q "\[${VERSION}\]" CHANGELOG.md; then
  pass "CHANGELOG references $VERSION"
else
  fail "CHANGELOG does not reference $VERSION"
fi

step "docs/index.html contains version $VERSION"
if grep -q "v${VERSION}" docs/index.html; then
  pass "docs/index.html references v$VERSION"
else
  fail "docs/index.html does not reference v$VERSION"
fi

# The stack contract gate compares this against VERSION across the whole stack,
# so a stale value fails CI in mq-agent, not here. Check it where it is written.
step ".mq/repo-contract.json contains version $VERSION"
CONTRACT_VERSION="$(python3 -c "import json; print(json.load(open('.mq/repo-contract.json'))['version'])")"
if [[ "$CONTRACT_VERSION" == "$VERSION" ]]; then
  pass "repo contract references $VERSION"
else
  fail "repo contract version '$CONTRACT_VERSION' != VERSION '$VERSION'"
fi

step "GitHub release tag"
if [[ "$DRY_RUN" -eq 1 ]]; then
  skip "dry-run — not checking whether v$VERSION is already released"
elif command -v gh >/dev/null 2>&1; then
  if gh release view "v${VERSION}" >/dev/null 2>&1; then
    fail "GitHub release v${VERSION} already exists — bump VERSION before releasing"
  else
    pass "v${VERSION} not yet released on GitHub"
  fi
else
  skip "gh CLI not available — skipping GitHub release check"
fi

step "Smoke tests"
_smoke_start=$FAILED
_smoke() {
  local s="$1" out
  if out="$("./tests/$s" 2>&1)"; then
    :
  else
    fail "$s"
    [[ "$JSON" -eq 1 ]] || printf '%s\n' "$out" >&2
  fi
}
_smoke smoke.sh
_smoke doctor-summary-smoke.sh
_smoke fix-planner-smoke.sh
_smoke session-memory-smoke.sh
_smoke timeline-smoke.sh
_smoke brief-smoke.sh
_smoke repo-status-smoke.sh
_smoke ci-status-smoke.sh
_smoke release-brief-smoke.sh
_smoke release-control-smoke.sh
_smoke audit-smoke.sh
_smoke stack-status-smoke.sh
_smoke hal-router-smoke.sh
_smoke intent-schema-smoke.sh
_smoke router-safety-smoke.sh
_smoke memory-status-smoke.sh
_smoke brain-smoke.sh
_smoke context-smoke.sh
_smoke route-control-smoke.sh
_smoke repo-memory-smoke.sh
_smoke agent-brief-smoke.sh
_smoke hello-smoke.sh
_smoke tools-smoke.sh
_smoke models-smoke.sh
_smoke provider-routing-smoke.sh
_smoke model-status-smoke.sh
_smoke model-test-smoke.sh
_smoke install-flow-smoke.sh
_smoke visual-hal-smoke.sh
_smoke prompt-regression-smoke.sh
_smoke plan-smoke.sh
_smoke critic-smoke.sh
_smoke execute-smoke.sh
_smoke learn-smoke.sh
_smoke env-status-smoke.sh
_smoke docs-smoke.sh
[[ "$FAILED" -eq "$_smoke_start" ]] && pass "all smoke tests passed"

step "Command surface consistency"
if ./tools/check-command-docs.sh >/dev/null 2>&1; then
  pass "command surface consistent"
else
  fail "command surface consistency check failed"
fi

if [[ "$JSON" -eq 1 ]]; then
  status=READY
  [[ "$FAILED" -ne 0 ]] && status=BLOCKED
  python3 - "$status" "$VERSION" ${BLOCKERS[@]+"${BLOCKERS[@]}"} <<'PY'
import json
import sys

status, version, *blockers = sys.argv[1:]
print(json.dumps({
    "schema": "repo_release_check.v1",
    "repo": "mq-hal",
    "status": status,
    "blockers": blockers,
    "warnings": [],
    "evidence": {"version": version},
}))
PY
  exit 0
fi

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
