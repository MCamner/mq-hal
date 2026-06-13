#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/mq-hal-pycache"

STATE_DIR="$(mktemp -d)"
BRAIN_DIR="$(mktemp -d)"
TMPBIN="$(mktemp -d)"
trap 'rm -rf "$STATE_DIR" "$BRAIN_DIR" "$TMPBIN"' EXIT

mkdir -p "$BRAIN_DIR/memory" "$BRAIN_DIR/learn" "$BRAIN_DIR/truth" "$BRAIN_DIR/reviews" "$STATE_DIR/learn"
printf '%s\n' "# Note" "brain release note" >"$BRAIN_DIR/memory/note.md"
printf '%s\n' '{"export":"learn"}' >"$BRAIN_DIR/learn/export.jsonl"
printf '%s\n' "# Latest release" >"$BRAIN_DIR/truth/latest-release.md"
printf '%s\n' "# Review" "release blocker clear" >"$BRAIN_DIR/reviews/review.md"
printf '%s\n' '{"lesson":"brain command"}' >"$STATE_DIR/learn/lessons.jsonl"

export MQ_HAL_STATE_DIR="$STATE_DIR"
export MQOBSIDIAN_PATH="$BRAIN_DIR"

cat >"$TMPBIN/obsidian" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$MQ_HAL_STATE_DIR/obsidian-calls.log"
case "$1" in
  read)
    printf '%s\n' "read:$2"
    ;;
  property:set)
    printf '%s\n' "property-set:${*:2}"
    ;;
  *)
    printf '%s\n' "unexpected:$*" >&2
    exit 2
    ;;
esac
SH
chmod +x "$TMPBIN/obsidian"

cat >"$TMPBIN/defuddle" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$MQ_HAL_STATE_DIR/defuddle-calls.log"
if [[ "$1" == "parse" && "$3" == "--md" ]]; then
  printf '%s\n' "# Defuddled Page" "" "Clean markdown body from $2."
  exit 0
fi
echo "unexpected defuddle args: $*" >&2
exit 2
SH
chmod +x "$TMPBIN/defuddle"
export PATH="$TMPBIN:$PATH"

echo "SMOKE: brain"

echo "[1/10] syntax"
python3 -m py_compile hal/brain.py

echo "[2/10] summary output"
./bin/mq-hal brain | grep -q "Brain Control Center"
./bin/mq-hal brain | grep -q "brain notes"
./bin/mq-hal brain | grep -q "Latest release"

echo "[3/10] health output"
./bin/mq-hal brain health | grep -q "Brain Health"
./bin/mq-hal brain health | grep -q "memory"

echo "[4/10] recent output"
./bin/mq-hal brain recent | grep -q "Brain Recent"
./bin/mq-hal brain recent | grep -q "latest-release.md"

echo "[5/10] search output"
./bin/mq-hal brain search release | grep -q "Brain Search"
./bin/mq-hal brain search release | grep -q "latest-release.md"

echo "[6/10] json output"
./bin/mq-hal brain --json | python3 -m json.tool >/dev/null
./bin/mq-hal brain search release --json | python3 -m json.tool >/dev/null

echo "[7/10] sample output"
./bin/mq-hal brain --sample | grep -q "Brain Control Center"

echo "[8/10] defuddle ingest bridge"
./bin/mq-hal brain ingest-url "https://example.com/docs/page" --root "$BRAIN_DIR" | grep -q "preview"
./bin/mq-hal brain ingest-url "https://example.com/docs/page" --root "$BRAIN_DIR" --confirm | grep -q "captured"
test -f "$BRAIN_DIR/inbox/defuddled-page.md"
grep -q "source_url" "$BRAIN_DIR/inbox/defuddled-page.md"
grep -q "parse https://example.com/docs/page --md" "$STATE_DIR/defuddle-calls.log"
if ./bin/mq-hal brain ingest-url "https://example.com/readme.md" --root "$BRAIN_DIR" --json >/tmp/mq-hal-md-url.json; then
  echo "ERROR: .md URL should be rejected" >&2
  exit 1
fi
python3 -m json.tool /tmp/mq-hal-md-url.json >/dev/null

echo "[9/10] obsidian open bridge"
./bin/mq-hal brain open memory/note.md | grep -q "read:path=memory/note.md"
./bin/mq-hal brain open "Note Title" --json | python3 -m json.tool >/dev/null
grep -q "read path=memory/note.md" "$STATE_DIR/obsidian-calls.log"

echo "[10/10] obsidian status sync requires confirm"
./bin/mq-hal brain sync-status memory/note.md --status active | grep -q "Preview only"
./bin/mq-hal brain sync-status memory/note.md --status active --confirm | grep -q "property-set:"
grep -q "property:set name=status value=active path=memory/note.md" "$STATE_DIR/obsidian-calls.log"

echo "OK: brain smoke test passed"
