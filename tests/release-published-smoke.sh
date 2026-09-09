#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

TOOL="$ROOT/tools/check-github-releases.sh"

echo "SMOKE: GitHub release publication gate"

echo "[1/7] syntax check"
bash -n "$TOOL"
bash -n "$ROOT/release-check.sh"

# A `gh` that answers from PUBLISHED and records every call it was asked to
# make, so the tests can assert on both the verdict and the network reached.
mkdir -p "$WORK/bin"
cat > "$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GH_CALLS"
if [[ "${1:-}" == "auth" ]]; then
  [[ "${GH_AUTHED:-1}" == "1" ]] && exit 0 || exit 1
fi
if [[ "${1:-}" == "release" && "${2:-}" == "view" ]]; then
  for v in ${PUBLISHED:-}; do
    [[ "$v" == "${3:-}" ]] && exit 0
  done
  exit 1
fi
exit 0
STUB
chmod +x "$WORK/bin/gh"
export PATH="$WORK/bin:$PATH"
export GH_CALLS="$WORK/calls.log"

changelog() {
  cat > "$WORK/CHANGELOG.md" <<'CL'
# Changelog

## [Unreleased]

## [2.5.0] - 2026-09-10

Cloud provider boundary.

## [2.4.0] - 2026-09-09

Runtime Provenance Presentation.

## [2.3.0] - 2026-08-23

Local-First Model Routing Control Room.

## [2.2.0] - 2026-08-03

Operator Feedback Polish.
CL
}
changelog

run() {
  : > "$GH_CALLS"
  PUBLISHED="$1" "$TOOL" --version "$2" --changelog "$WORK/CHANGELOG.md" 2>&1
}

echo "[2/7] the predecessor comes from the changelog, never from the tag list"
# Tags carry things that are not releases: archive/… evidence refs and a
# lightweight v2.1.0 from before the annotated-tag convention. A gate that
# walked the tags would have to know which of those count.
if grep -nE 'git (tag|for-each-ref|describe|rev-list)' "$TOOL"; then
  echo "FAIL: the gate reads git tags; predecessor must come from CHANGELOG.md" >&2
  exit 1
fi
out="$(run "v2.4.0" 2.5.0)"
grep -q "predecessor v2.4.0 is published" <<<"$out" || { echo "$out"; exit 1; }
# [Unreleased] is a heading, not a version, and must never be chosen.
if grep -q "Unreleased" <<<"$out"; then
  echo "FAIL: Unreleased treated as a version"; exit 1
fi
echo "  predecessor of 2.5.0 is 2.4.0, no git tag is read: OK"

echo "[3/7] a version already published is still a duplicate-release failure"
out="$(run "v2.5.0 v2.4.0" 2.5.0 || true)"
grep -q "FAIL: v2.5.0 is already published" <<<"$out" || { echo "$out"; exit 1; }
set +e
run "v2.5.0 v2.4.0" 2.5.0 >/dev/null 2>&1
status=$?
set -e
[[ "$status" -ne 0 ]] || { echo "FAIL: duplicate release exited 0"; exit 1; }
echo "  the check A1 already had still fails on a duplicate: OK"

echo "[4/7] a predecessor that was never published fails"
# The exact miss this gate exists for: 2.4.0 declared, tagged, never released,
# and the next version bump would have buried it forever.
set +e
out="$(run "v2.3.0" 2.5.0 2>&1)"
status=$?
set -e
[[ "$status" -ne 0 ]] || { echo "FAIL: missing predecessor exited 0"; echo "$out"; exit 1; }
grep -q "FAIL: predecessor v2.4.0" <<<"$out" || { echo "$out"; exit 1; }
grep -q "OK: v2.5.0 is not yet published" <<<"$out" || { echo "$out"; exit 1; }
# And the failure has to name the version, or an operator cannot act on it.
grep -q "no published GitHub release" <<<"$out" || { echo "$out"; exit 1; }
echo "  v2.4.0 tagged but unpublished → FAIL naming it: OK"

echo "[5/7] the v2.3/v2.4 shape exactly: two in a row, one bump away from silence"
set +e
out="$(run "v2.2.0" 2.4.0 2>&1)"; status=$?
set -e
[[ "$status" -ne 0 ]] || { echo "FAIL: 2.4.0 with unpublished 2.3.0 exited 0"; exit 1; }
grep -q "FAIL: predecessor v2.3.0" <<<"$out" || { echo "$out"; exit 1; }
# Once both are published the same repo state passes, which is what the
# retroactive publication produced.
out="$(run "v2.3.0 v2.2.0" 2.4.0 2>&1)"
grep -q "OK: predecessor v2.3.0 is published" <<<"$out" || { echo "$out"; exit 1; }
echo "  the historical miss fails, the repaired history passes: OK"

echo "[6/7] the edges skip rather than guess"
out="$(run "v2.2.0" 2.2.0 2>&1 || true)"
grep -q "SKIP: v2.2.0 is the oldest declared version" <<<"$out" || { echo "$out"; exit 1; }
out="$(run "" 9.9.9 2>&1 || true)"
grep -q "SKIP: 9.9.9 is not declared" <<<"$out" || { echo "$out"; exit 1; }
: > "$GH_CALLS"
out="$(GH_AUTHED=0 PUBLISHED="" "$TOOL" --version 2.5.0 --changelog "$WORK/CHANGELOG.md" 2>&1)"
grep -q "SKIP: gh is not authenticated" <<<"$out" || { echo "$out"; exit 1; }
# Unauthenticated, every lookup fails and would read as "nothing is published".
# Not knowing must not become a verdict, so no release lookup is attempted.
if grep -q "release view" "$GH_CALLS"; then
  echo "FAIL: looked up releases without auth"; exit 1
fi
echo "  oldest version, unknown version and no auth all skip: OK"

echo "[7/7] --dry-run and --json reach no network"
python3 - "$ROOT" <<'PY'
import re
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "release-check.sh").read_text()

# --json is the stack's release preflight and is consumed by mq-agent. It must
# stay network-free, which it is because --json implies --dry-run.
assert re.search(r'\[\[ "\$JSON" -eq 1 \]\] && DRY_RUN=1', source), (
    "--json no longer implies --dry-run; the preflight would start doing network I/O"
)

# Structural rather than executed: running release-check.sh from inside its own
# smoke suite would recurse. The invariant is that the only call to the gate
# sits in the branch --dry-run does not take.
calls = [i for i, line in enumerate(source.splitlines())
         if "check-github-releases.sh" in line and not line.strip().startswith("#")]
assert len(calls) == 1, f"expected one call to the gate, found {len(calls)}"

lines = source.splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith('step "GitHub release'))
guard = next(i for i in range(start, calls[0]) if 'DRY_RUN" -eq 1 ]]; then' in lines[i])
skipped = next(i for i in range(guard, calls[0]) if lines[i].strip().startswith("skip "))
assert guard < skipped < calls[0], (
    "the gate is not behind the --dry-run guard; CI and the preflight would "
    "start reading GitHub"
)
print("  --json implies --dry-run; the single gate call is behind that guard: OK")
PY

echo "OK: GitHub release publication gate smoke test passed"
