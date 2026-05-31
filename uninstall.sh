#!/usr/bin/env bash
set -euo pipefail

PREFIX="${MQ_HAL_PREFIX:-$HOME/bin}"
TARGET="$PREFIX/mq-hal"

if [[ -L "$TARGET" ]]; then
  rm "$TARGET"
  echo "Removed $TARGET"
elif [[ -e "$TARGET" ]]; then
  echo "Refusing to remove non-symlink: $TARGET" >&2
  exit 1
else
  echo "mq-hal link not found at $TARGET"
fi
