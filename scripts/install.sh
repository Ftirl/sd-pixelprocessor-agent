#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
if [ -n "${AGENT_SKILLS_HOME:-}" ]; then
  DEST_ROOT="$AGENT_SKILLS_HOME"
elif [ -n "${CODEX_HOME:-}" ]; then
  DEST_ROOT="$CODEX_HOME/skills"
else
  DEST_ROOT="$HOME/.codex/skills"
fi

mkdir -p "$DEST_ROOT"
DEST_ROOT=$(CDPATH= cd -- "$DEST_ROOT" && pwd)
DEST="$DEST_ROOT/sd-pixelprocessor-agent"
if [ "$SOURCE_DIR" = "$DEST" ]; then
  printf 'Already installed at: %s\n' "$DEST"
  exit 0
fi
if [ -e "$DEST" ]; then
  BACKUP="$DEST.backup.$(date +%Y%m%d%H%M%S)"
  cp -R "$DEST" "$BACKUP"
  echo "Existing skill backed up to: $BACKUP"
  rm -rf "$DEST"
fi
cp -R "$SOURCE_DIR" "$DEST"
rm -rf "$DEST/scripts/__pycache__" 2>/dev/null || true
printf 'Installed: %s\n' "$DEST"
printf 'Invoke with: $sd-pixelprocessor-agent\n'
