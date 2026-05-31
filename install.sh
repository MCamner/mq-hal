#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${MQ_HAL_PREFIX:-$HOME/bin}"
TARGET="$PREFIX/mq-hal"

mkdir -p "$PREFIX"
ln -sf "$ROOT/bin/mq-hal" "$TARGET"

echo "mq-hal installed:"
echo "  $TARGET -> $ROOT/bin/mq-hal"
echo
echo "Add this to your shell profile if needed:"
echo "  export PATH=\"$PREFIX:\$PATH\""
